"""CSV 文件解析"""
import csv


async def parse_csv(file_path: str) -> str:
    """解析 CSV 文件，将每行转为文本片段"""
    rows_text = []
    for encoding in ("utf-8", "gbk"):
        try:
            with open(file_path, "r", encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                header = None
                for row in reader:
                    if header is None:
                        header = row
                        continue
                    # 将每行数据转为 "列名: 值" 格式的文本
                    if header and len(row) == len(header):
                        line_parts = [
                            f"{h}: {v}" for h, v in zip(header, row) if v
                        ]
                        rows_text.append(", ".join(line_parts))
                    else:
                        rows_text.append(", ".join(row))
            return "\n".join(rows_text)
        except UnicodeDecodeError:
            rows_text = []  # 重置
            continue
        except Exception:
            rows_text = []
            continue

    # 两种编码都失败，用 UTF-8 忽略错误字符
    with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        header = None
        for row in reader:
            if header is None:
                header = row
                continue
            if header and len(row) == len(header):
                line_parts = [f"{h}: {v}" for h, v in zip(header, row) if v]
                rows_text.append(", ".join(line_parts))
            else:
                rows_text.append(", ".join(row))
    return "\n".join(rows_text)
