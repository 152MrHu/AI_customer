"""分页工具"""
from fastapi import Query
from dataclasses import dataclass


@dataclass
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_page_params(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
) -> PageParams:
    """FastAPI 依赖：解析分页参数"""
    return PageParams(page=page, page_size=page_size)
