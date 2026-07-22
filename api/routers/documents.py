import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
)

from api.dependencies import get_file_registry
from api.schemas import (
    DeleteDocumentResponse,
    DocumentSummary,
    UploadDocumentResponse,
)
from rag.file_registry import FileRegistry
from rag.knowledge_base import (
    add_file_to_knowledge_base,
    delete_file_from_knowledge_base,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    tags=["knowledge-base"],
)


@router.post(
    "/documents",
    response_model=UploadDocumentResponse,
)
def upload_document(
    file: UploadFile,
) -> UploadDocumentResponse:
    """上传文件并将其加入知识库。"""

    try:
        file_name = file.filename or ""

        if not file_name:
            raise HTTPException(
                status_code=400,
                detail="文件名不能为空",
            )

        file_suffix = Path(
            file_name
        ).suffix.lower()

        allowed_suffixes = {
            ".pdf",
            ".txt",
            ".docx",
        }

        if file_suffix not in allowed_suffixes:
            raise HTTPException(
                status_code=400,
                detail=(
                    "只支持 PDF、TXT 和 DOCX 文件"
                ),
            )

        file_bytes = file.file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="文件内容不能为空",
            )

        result = add_file_to_knowledge_base(
            file_name=file_name,
            file_bytes=file_bytes,
        )

        return UploadDocumentResponse(
            message=result["message"],
            duplicate=result.get(
                "duplicate",
                False,
            ),
            file_id=result.get("file_id"),
            file_name=result.get(
                "file_name",
                file_name,
            ),
            document_count=result.get(
                "document_count"
            ),
            chunk_count=result.get(
                "chunk_count",
                0,
            ),
        )

    except HTTPException:
        raise

    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception("文件入库失败")

        raise HTTPException(
            status_code=500,
            detail="文件入库失败，请稍后重试",
        ) from error

    finally:
        file.file.close()


@router.get(
    "/documents",
    response_model=list[DocumentSummary],
)
def get_documents(
    file_registry: FileRegistry = Depends(
        get_file_registry
    ),
) -> list[DocumentSummary]:
    """获取知识库中的全部文件。"""

    try:
        files = file_registry.list_files()

        return [
            DocumentSummary(
                file_id=file_info["file_id"],
                file_name=file_info["file_name"],
                file_type=file_info.get(
                    "file_type",
                    "",
                ),
                upload_time=file_info.get(
                    "upload_time",
                    "",
                ),
                document_count=file_info.get(
                    "document_count",
                    0,
                ),
                chunk_count=file_info.get(
                    "chunk_count",
                    0,
                ),
                status=file_info.get(
                    "status",
                    "active",
                ),
            )
            for file_info in files
        ]

    except Exception as error:
        logger.exception(
            "读取知识库文件列表失败"
        )

        raise HTTPException(
            status_code=500,
            detail="读取知识库文件列表失败",
        ) from error


@router.delete(
    "/documents/{file_id}",
    response_model=DeleteDocumentResponse,
)
def delete_document(
    file_id: str,
) -> DeleteDocumentResponse:
    """删除知识库文件及其全部向量。"""

    try:
        result = (
            delete_file_from_knowledge_base(
                file_id=file_id
            )
        )

        return DeleteDocumentResponse(
            message=result["message"],
            file_id=result["file_id"],
            file_name=result.get(
                "file_name"
            ),
            deleted_chunk_count=result.get(
                "deleted_chunk_count",
                0,
            ),
            original_file_deleted=result.get(
                "original_file_deleted",
                False,
            ),
            rollback_used=result.get(
                "rollback_used",
                False,
            ),
            cleanup_warnings=result.get(
                "cleanup_warnings",
                [],
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        logger.exception(
            "知识库文件删除失败"
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception(
            "知识库文件删除发生未知异常"
        )

        raise HTTPException(
            status_code=500,
            detail="知识库文件删除失败",
        ) from error