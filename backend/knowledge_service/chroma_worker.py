"""ChromaDB 子进程 worker

独立进程执行 ChromaDB 读写操作，彻底隔离主 knowledge_service 进程。

用法（通过 subprocess 调用）：
  python chroma_worker.py create_collection <kb_id>
  python chroma_worker.py add <kb_id> <data_file.json>
  python chroma_worker.py delete_by_doc <kb_id> <document_id>
  python chroma_worker.py delete_collection <kb_id>
  python chroma_worker.py search <data_file.json>
  python chroma_worker.py count <kb_id>

数据文件格式（JSON）：
  add: {"chunks": [...], "embeddings": [[...]], "document_id": N, "file_name": "..."}
  search: {"kb_id": N, "query_embedding": [...], "top_k": 5}

结果通过 stdout JSON 输出，错误通过 stderr JSON 输出。
"""
import sys
import json
import time

import chromadb

from common.config import settings

# 操作超时警告阈值（秒）
_SLOW_THRESHOLD = 5


def _get_client():
    """创建独立的 ChromaDB 客户端"""
    return chromadb.PersistentClient(path=settings.chroma_path)


def _do_create_collection(kb_id: int):
    client = _get_client()
    client.get_or_create_collection(
        name=f"kb_{kb_id}",
        metadata={"hnsw:space": "cosine"},
    )
    print(json.dumps({"status": "ok", "action": "create_collection", "kb_id": kb_id}))


def _do_add_chunks(kb_id: int, data: dict):
    chunks = data["chunks"]
    embeddings = data["embeddings"]
    document_id = data["document_id"]
    file_name = data["file_name"]

    client = _get_client()
    # 使用 get_or_create_collection：如果 collection 不存在则自动创建
    # （chroma_data 目录重建后，旧 collection 会丢失，需要自动恢复）
    collection = client.get_or_create_collection(
        name=f"kb_{kb_id}",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"{document_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "document_id": document_id,
            "file_name": file_name,
            "chunk_index": i,
            "source": file_name,
        }
        for i in range(len(chunks))
    ]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    print(json.dumps({
        "status": "ok",
        "action": "add_chunks",
        "kb_id": kb_id,
        "document_id": document_id,
        "chunk_count": len(chunks),
    }))


def _do_delete_by_document(kb_id: int, document_id: int):
    client = _get_client()
    try:
        collection = client.get_collection(name=f"kb_{kb_id}")
    except Exception:
        # collection 不存在，无需删除
        print(json.dumps({"status": "ok", "action": "delete_skipped", "reason": "collection_not_found"}))
        return
    try:
        collection.delete(where={"document_id": document_id})
        print(json.dumps({
            "status": "ok",
            "action": "delete_by_document",
            "kb_id": kb_id,
            "document_id": document_id,
        }))
    except Exception as e:
        # 删除失败不致命（向量残留不影响功能）
        print(json.dumps({"status": "warning", "action": "delete_by_document", "error": str(e)}))


def _do_delete_collection(kb_id: int):
    client = _get_client()
    try:
        client.delete_collection(name=f"kb_{kb_id}")
        print(json.dumps({"status": "ok", "action": "delete_collection", "kb_id": kb_id}))
    except Exception:
        # collection 不存在也没关系
        print(json.dumps({"status": "ok", "action": "delete_collection", "reason": "not_found"}))


def _do_search(data: dict):
    """向量检索（读取操作）"""
    kb_id = data.get("kb_id")
    query_embedding = data.get("query_embedding")
    top_k = data.get("top_k", settings.TOP_K)

    if not kb_id or not query_embedding:
        print(json.dumps({"status": "error", "message": "缺少 kb_id 或 query_embedding"}))
        return

    client = _get_client()
    try:
        collection = client.get_collection(name=f"kb_{kb_id}")
    except Exception:
        # collection 不存在，返回空结果
        print(json.dumps({"status": "ok", "action": "search", "items": []}))
        return

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not results or not results.get("ids") or not results["ids"][0]:
        print(json.dumps({"status": "ok", "action": "search", "items": []}))
        return

    ids = results["ids"][0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    items = []
    for i in range(len(ids)):
        distance = distances[i] if i < len(distances) else 1.0
        score = round(1.0 - distance, 4)
        meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
        document = documents[i] if i < len(documents) else ""
        doc_name = (
            meta.get("file_name") or meta.get("doc_name")
            or meta.get("source") or "未知文档"
        )
        items.append({
            "doc_name": doc_name,
            "score": score,
            "snippet": document[:200] if document else "",
            "document": document,
        })

    print(json.dumps({"status": "ok", "action": "search", "items": items}))


def _do_count(kb_id: int):
    """查询向量数量（读取操作）"""
    client = _get_client()
    try:
        collection = client.get_collection(name=f"kb_{kb_id}")
        count = collection.count()
        print(json.dumps({"status": "ok", "action": "count", "kb_id": kb_id, "count": count}))
    except Exception:
        # collection 不存在，返回 0
        print(json.dumps({"status": "ok", "action": "count", "kb_id": kb_id, "count": 0}))


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "message": f"用法: {sys.argv[0]} <action> <args...>"}), file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]
    start = time.time()

    try:
        if action == "create_collection":
            kb_id = int(sys.argv[2])
            _do_create_collection(kb_id)

        elif action == "add":
            kb_id = int(sys.argv[2])
            data_file = sys.argv[3]
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            _do_add_chunks(kb_id, data)

        elif action == "delete_by_doc":
            kb_id = int(sys.argv[2])
            document_id = int(sys.argv[3])
            _do_delete_by_document(kb_id, document_id)

        elif action == "delete_collection":
            kb_id = int(sys.argv[2])
            _do_delete_collection(kb_id)

        elif action == "search":
            data_file = sys.argv[2]
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            _do_search(data)

        elif action == "count":
            kb_id = int(sys.argv[2])
            _do_count(kb_id)

        else:
            print(json.dumps({"status": "error", "message": f"未知操作: {action}"}), file=sys.stderr)
            sys.exit(1)

        elapsed = time.time() - start
        if elapsed > _SLOW_THRESHOLD:
            pass  # 慢操作只记录时间，不影响结果

    except Exception as e:
        elapsed = time.time() - start
        print(json.dumps({
            "status": "error",
            "action": action,
            "error": str(e),
            "elapsed": round(elapsed, 2),
        }), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
