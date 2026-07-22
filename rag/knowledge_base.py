import shutil
import uuid
from datetime import datetime
from pathlib import Path

from config import (
    BACKUP_DIR,
    FAISS_DIR,
    TRASH_DIR,
    UPLOAD_DIR,
)
from langchain_community.vectorstores import FAISS

from rag.embedding import get_embedding_model
from rag.file_registry import FileRegistry
from rag.loader import loader_document
from rag.splitter import split_document

#创建类对象
file_registry = FileRegistry()
def save_uploaded_file(
    file_name: str,
    file_bytes: bytes,
) -> Path:
    """
    保存用户上传的原始文件。
    """

    file_path = UPLOAD_DIR / file_name

    file_path.write_bytes(file_bytes)

    return file_path


def vectorstore_exists() -> bool:
    """
    判断本地 FAISS 向量库是否存在。
    """
    #判断这个路径，是为true，否为false
    return (
        (FAISS_DIR / "index.faiss").exists()
        and (FAISS_DIR / "index.pkl").exists()
    )


def load_vectorstore():
    """
    加载本地 FAISS 向量库。
    """

    return FAISS.load_local(
        str(FAISS_DIR),#地址
        get_embedding_model(),#embedding model
        allow_dangerous_deserialization=True, #default
    )
    #这里还是返回一个向量实例加载对象

def create_delete_backup(operation_id: str,) -> tuple[Path, Path, Path]:
    """
    删除操作开始前，备份：
    1. Registry 文件
    2. FAISS 索引目录
    返回：operation_backup_dir，registry_backup_path，faiss_backup_path三个文件路径，并且已经被完全备份
    """
    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )#备份的主目录

    operation_backup_dir = (
        BACKUP_DIR / operation_id
    )

    registry_backup_path = (
        operation_backup_dir
        / "file_registry.json"
    )

    faiss_backup_path = (
        operation_backup_dir
        / "faiss_db"
    )

    try:
        operation_backup_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        # 1. 备份 Registry
        if not file_registry.registry_path.exists():
            raise FileNotFoundError(
                "Registry 文件不存在，无法备份"
            )

        shutil.copy2(
            file_registry.registry_path,
            registry_backup_path,
        )

        # 2. 备份 FAISS
        if not vectorstore_exists():
            raise FileNotFoundError(
                "FAISS 索引不存在，无法备份"
            )

        shutil.copytree(
            FAISS_DIR,
            faiss_backup_path,
        )

    except Exception:
        shutil.rmtree(
            operation_backup_dir,
            ignore_errors=True,
        )
        raise

    return (
        operation_backup_dir,
        registry_backup_path,
        faiss_backup_path,
    )

def restore_delete_backup(
    registry_backup_path: Path,
    faiss_backup_path: Path,
    original_file_path: Path,
    trash_file_path: Path,
) -> list[str]:
    """
    删除失败时恢复：
    1. 原始文件
    2. FAISS
    3. Registry

    返回回滚失败信息列表。
    空列表表示回滚全部成功。
    """

    rollback_errors: list[str] = []

    # 1. 恢复原始文件
    try:
        if trash_file_path.exists():
            original_file_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if original_file_path.exists():
                raise FileExistsError(
                    "原始文件路径已经存在，"
                    "无法从 trash 恢复"
                )

            shutil.move(
                str(trash_file_path),
                str(original_file_path),
            )

    except Exception as error:
        rollback_errors.append(
            f"原始文件恢复失败：{error}"
        )

    # 2. 恢复 FAISS
    try:
        if not faiss_backup_path.exists():
            raise FileNotFoundError(
                "FAISS 备份不存在"
            )

        if FAISS_DIR.exists():
            shutil.rmtree(FAISS_DIR)

        shutil.copytree(
            faiss_backup_path,
            FAISS_DIR,
        )

    except Exception as error:
        rollback_errors.append(
            f"FAISS 恢复失败：{error}"
        )

    # 3. 恢复 Registry
    try:
        if not registry_backup_path.exists():
            raise FileNotFoundError(
                "Registry 备份不存在"
            )

        shutil.copy2(
            registry_backup_path,
            file_registry.registry_path,
        )

    except Exception as error:
        rollback_errors.append(
            f"Registry 恢复失败：{error}"
        )

    return rollback_errors

def verify_file_deleted( file_id: str,original_file_path: Path,chunk_ids: list[str],) -> None:
    """
    验证文件是否在三个位置全部删除。
    """

    # 1. Registry 不应存在
    if file_registry.get_by_id(file_id) is not None:
        raise RuntimeError(
            "删除验证失败：Registry 记录仍然存在"
        )

    # 2. 原始文件不应存在
    if original_file_path.exists():
        raise RuntimeError(
            "删除验证失败：原始文件仍然存在"
        )

    # 3. FAISS 不应存在对应 Chunk
    if vectorstore_exists():
        vectorstore = load_vectorstore()

        current_ids = set(
            vectorstore
            .index_to_docstore_id
            .values()
        )

        remaining_chunk_ids = (
            set(chunk_ids) & current_ids
        )

        if remaining_chunk_ids:
            raise RuntimeError(
                "删除验证失败："
                f"FAISS 仍残留 "
                f"{len(remaining_chunk_ids)} 个 Chunk"
            )



def delete_chunks_from_vectorstore(
    chunk_ids: list[str],
) -> int:
    """
    根据 Chunk ID 删除 FAISS 中对应的向量。
    """

    # 防止传入 None、元组等类型
    chunk_ids = list(chunk_ids or [])

    print(
        f"[delete_chunks] 收到 Chunk 数量："
        f"{len(chunk_ids)}"
    )

    # 不允许静默跳过
    if not chunk_ids:
        raise ValueError(
            "没有收到 chunk_ids，拒绝继续删除"
        )

    if not vectorstore_exists():
        raise FileNotFoundError(
            "FAISS 向量库不存在"
        )

    vectorstore = load_vectorstore()

    # 获取删除前真实存在的 FAISS ID
    current_ids = set(
        vectorstore.index_to_docstore_id.values()
    )

    target_ids = set(chunk_ids)

    existing_target_ids = (
        target_ids & current_ids
    )

    missing_ids = (
        target_ids - current_ids
    )

    print(
        f"[delete_chunks] FAISS 中实际匹配："
        f"{len(existing_target_ids)}"
    )

    if missing_ids:
        raise RuntimeError(
            f"有 {len(missing_ids)} 个 Chunk ID "
            "在 FAISS 中不存在，停止删除"
        )

    delete_result = vectorstore.delete(
        ids=chunk_ids
    )

    print(
        "[delete_chunks] FAISS delete 返回：",
        delete_result,
    )

    if delete_result is not True:
        raise RuntimeError(
            f"FAISS 删除失败，返回值："
            f"{delete_result}"
        )

    # 将删除后的 FAISS 写回硬盘
    vectorstore.save_local(
        str(FAISS_DIR)
    )

    # 重新从硬盘加载，验证持久化结果
    reloaded_vectorstore = load_vectorstore()

    remaining_ids = set(
        reloaded_vectorstore
        .index_to_docstore_id
        .values()
    )

    remaining_target_ids = (
        target_ids & remaining_ids
    )

    if remaining_target_ids:
        raise RuntimeError(
            f"FAISS 保存后仍残留 "
            f"{len(remaining_target_ids)} 个 Chunk"
        )

    return len(chunk_ids)

 

def delete_file_from_knowledge_base(
    file_id: str,
    simulate_failure_step: str | None = None,
) -> dict:
    """
    根据 file_id 安全删除知识库文件。

    删除内容：
    1. FAISS Chunk
    2. 原始文件
    3. Registry 记录

    任意步骤失败时：
    1. 恢复原始文件
    2. 恢复 FAISS
    3. 恢复 Registry

    simulate_failure_step 仅用于测试回滚：
    - after_file_move
    - after_faiss_delete
    - after_registry_delete
    """

    if not file_id:
        raise ValueError(
            "file_id 不能为空"
        )

    # 1. 查询 Registry
    file_info = file_registry.get_by_id(
        file_id
    )

    if file_info is None:
        raise FileNotFoundError(
            f"知识库中不存在该文件：{file_id}"
        )

    # 2. 读取并校验 chunk_ids
    chunk_ids = file_info.get(
        "chunk_ids"
    )

    if not isinstance(chunk_ids, list):
        raise RuntimeError(
            "Registry 中的 chunk_ids "
            "不存在或不是列表"
        )

    if not chunk_ids:
        raise RuntimeError(
            "Registry 中的 chunk_ids 为空，"
            "拒绝继续删除"
        )

    # 3. 读取并校验原始文件路径
    file_path_value = file_info.get(
        "file_path"
    )

    if not file_path_value:
        raise RuntimeError(
            "Registry 中缺少 file_path"
        )

    original_file_path = Path(
        file_path_value
    )

    if not original_file_path.exists():
        raise FileNotFoundError(
            f"原始文件不存在："
            f"{original_file_path}"
        )

    # 4. 创建本次操作 ID
    operation_id = str(uuid.uuid4())

    TRASH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    trash_file_path = (
        TRASH_DIR
        / f"{operation_id}_{original_file_path.name}"
    )

    # 5. 删除前完整备份
    (
        operation_backup_dir,
        registry_backup_path,
        faiss_backup_path,
    ) = create_delete_backup(
        operation_id
    )

    deleted_chunk_count = 0

    try:
        # 6. 原始文件先移入 trash
        shutil.move(
            str(original_file_path),
            str(trash_file_path),
        )

        print(
            "[delete_file] 原始文件已移入 trash：",
            trash_file_path,
        )

        if (
            simulate_failure_step
            == "after_file_move"
        ):
            raise RuntimeError(
                "模拟异常：原始文件移动后失败"
            )

        # 7. 删除 FAISS Chunk
        deleted_chunk_count = (
            delete_chunks_from_vectorstore(
                chunk_ids
            )
        )

        if deleted_chunk_count != len(
            chunk_ids
        ):
            raise RuntimeError(
                "实际删除 Chunk 数量与 "
                "Registry 记录不一致"
            )

        if (
            simulate_failure_step
            == "after_faiss_delete"
        ):
            raise RuntimeError(
                "模拟异常：FAISS 删除后失败"
            )

        # 8. 删除 Registry 记录
        removed_file = file_registry.remove(
            file_id
        )

        if removed_file is None:
            raise RuntimeError(
                "Registry 记录删除失败"
            )

        if (
            simulate_failure_step
            == "after_registry_delete"
        ):
            raise RuntimeError(
                "模拟异常：Registry 删除后失败"
            )

        # 9. 最终验证
        verify_file_deleted(
            file_id=file_id,
            original_file_path=(
                original_file_path
            ),
            chunk_ids=chunk_ids,
        )

    except Exception as original_error:
        print(
            "[delete_file] 删除发生异常，"
            "开始回滚：",
            original_error,
        )

        rollback_errors = (
            restore_delete_backup(
                registry_backup_path=(
                    registry_backup_path
                ),
                faiss_backup_path=(
                    faiss_backup_path
                ),
                original_file_path=(
                    original_file_path
                ),
                trash_file_path=(
                    trash_file_path
                ),
            )
        )

        if rollback_errors:
            # 回滚不完整时保留备份目录，
            # 方便手动恢复
            raise RuntimeError(
                "文件删除失败，并且回滚不完整："
                + "；".join(rollback_errors)
                + f"。备份保留在："
                f"{operation_backup_dir}"
            ) from original_error

        # 回滚成功后清理本次备份
        shutil.rmtree(
            operation_backup_dir,
            ignore_errors=True,
        )

        raise RuntimeError(
            f"文件删除失败，但已成功回滚："
            f"{original_error}"
        ) from original_error

    # 10. 到这里说明删除已经提交成功
    cleanup_warnings: list[str] = []

    # 永久删除 trash 中的原始文件
    try:
        if trash_file_path.exists():
            trash_file_path.unlink()

    except Exception as error:
        cleanup_warnings.append(
            f"trash 清理失败：{error}"
        )

    # 删除备份目录
    try:
        shutil.rmtree(
            operation_backup_dir,
        )

    except Exception as error:
        cleanup_warnings.append(
            f"备份目录清理失败：{error}"
        )

    return {
        "message": "知识库文件删除成功",
        "file_id": file_id,
        "file_name": file_info.get(
            "file_name"
        ),
        "deleted_chunk_count": (
            deleted_chunk_count
        ),
        "original_file_deleted": True,
        "rollback_used": False,
        "cleanup_warnings": (
            cleanup_warnings
        ),
    }



def add_file_to_knowledge_base(
    file_name: str,
    file_bytes: bytes,
) -> dict:

    if not file_name:
        raise ValueError("文件名不能为空")

    if not file_bytes:
        raise ValueError("文件内容不能为空")

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    FAISS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_type = Path(file_name).suffix.lower()

    supported_file_types = {
        ".pdf",
        ".txt",
        ".docx",
    }

    if file_type not in supported_file_types:
        raise ValueError(
            f"不支持的文件格式：{file_type}"
        )

    file_hash = file_registry.calculate_file_hash(
        file_bytes
    )

    existing_file = file_registry.get_by_hash(
        file_hash
    )

    if existing_file is not None:
        return {
            "message": "该文件已经存在于知识库中",
            "duplicate": True,
            "file_id": existing_file["file_id"],
            "file_name": existing_file["file_name"],
            "chunk_count": existing_file["chunk_count"],
        }

    file_id = str(uuid.uuid4())
    stored_file_name = f"{file_id}{file_type}"
    file_path = UPLOAD_DIR / stored_file_name

    upload_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # 保存前记录原来是否存在索引
    had_vectorstore = vectorstore_exists()

    chunk_ids: list[str] = []
    faiss_saved = False

    try:
        file_path.write_bytes(file_bytes)

        documents = loader_document(
            str(file_path)
        )

        if not documents:
            raise ValueError(
                "文件没有解析出有效内容"
            )

        chunks = split_document(documents)

        if not chunks:
            raise ValueError(
                "文档切分后没有生成 Chunk"
            )

        for chunk_index, chunk in enumerate(chunks):
            chunk_id = (
                f"{file_id}_chunk_{chunk_index}"
            )

            chunk_ids.append(chunk_id)

            chunk.metadata.update(
                {
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_hash": file_hash,
                    "file_path": str(file_path),
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "upload_time": upload_time,
                }
            )

        if had_vectorstore:
            vectorstore = load_vectorstore()

            vectorstore.add_documents(
                documents=chunks,
                ids=chunk_ids,
            )

        else:
            vectorstore = FAISS.from_documents(
                documents=chunks,
                embedding=get_embedding_model(),
                ids=chunk_ids,
            )

        vectorstore.save_local(
            str(FAISS_DIR)
        )

        faiss_saved = True

        file_info = {
            "file_id": file_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_path": str(file_path),
            "file_hash": file_hash,
            "upload_time": upload_time,
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "chunk_ids": chunk_ids,
            "status": "active",
            "version": 1,
        }

        file_registry.add(file_info)

        return {
            "message": "文件已成功加入知识库",
            "duplicate": False,
            "file_id": file_id,
            "file_name": file_name,
            "document_count": len(documents),
            "chunk_count": len(chunks),
        }

    except Exception as original_error:
        rollback_errors = []

        # Registry 有可能已经写入后又发生异常
        try:
            registered_file = file_registry.get_by_id(
                file_id
            )

            if registered_file is not None:
                file_registry.remove(file_id)

        except Exception as error:
            rollback_errors.append(
                f"Registry 回滚失败：{error}"
            )

        # 回滚 FAISS
        if faiss_saved:
            try:
                if had_vectorstore:
                    rollback_vectorstore = (
                        load_vectorstore()
                    )

                    rollback_vectorstore.delete(
                        ids=chunk_ids
                    )

                    rollback_vectorstore.save_local(
                        str(FAISS_DIR)
                    )

                else:
                    # 原来没有索引，这次创建失败，
                    # 直接删除本次生成的整个索引目录
                    shutil.rmtree(
                        FAISS_DIR,
                        ignore_errors=True,
                    )

            except Exception as error:
                rollback_errors.append(
                    f"FAISS 回滚失败：{error}"
                )

        # 删除本次上传的原始文件
        try:
            if file_path.exists():
                file_path.unlink()

        except Exception as error:
            rollback_errors.append(
                f"原始文件回滚失败：{error}"
            )

        if rollback_errors:
            raise RuntimeError(
                "文件入库失败，同时部分回滚操作失败："
                + "；".join(rollback_errors)
            ) from original_error

        raise

