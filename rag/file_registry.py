import hashlib
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from config import DATA_DIR


class FileRegistry:
    """
    管理知识库中的文件登记信息。

    Registry 只保存文件管理信息，
    不保存文件正文，也不保存向量。
    """

    def __init__(
        self,
        registry_path: str | Path | None = None,
    ):
        if registry_path is None:
            registry_path = (
                DATA_DIR / "file_registry.json"
            )

        self.registry_path = Path(registry_path)

        # 使用可重入锁，避免同一进程中并发修改 Registry
        self._lock = threading.RLock()

        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.registry_path.exists():
            self.create_empty_registry()

    @staticmethod
    def _empty_registry() -> dict[str, Any]:
        """
        返回一个空 Registry 数据结构。
        """
        return {
            "version": 1,
            "files": {},
        }

    def create_empty_registry(self) -> None:
        """
        创建空 Registry。
        """
        self.save(
            self._empty_registry()
        )

    def load(self) -> dict[str, Any]:
        """
        从硬盘读取 Registry。

        返回 Python 字典。
        """
        with self._lock:
            if not self.registry_path.exists():
                self.create_empty_registry()

            try:
                with self.registry_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    registry = json.load(file)

            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Registry JSON 格式错误：{error}"
                ) from error

            except OSError as error:
                raise OSError(
                    f"Registry 读取失败：{error}"
                ) from error

            # 基础结构校验
            if not isinstance(registry, dict):
                raise ValueError(
                    "Registry 根节点必须是字典"
                )

            if "version" not in registry:
                registry["version"] = 1

            if "files" not in registry:
                registry["files"] = {}

            if not isinstance(
                registry["files"],
                dict,
            ):
                raise ValueError(
                    "Registry 中的 files 必须是字典"
                )

            return registry

    def save(
        self,
        registry: dict[str, Any],
    ) -> None:
        """
        原子保存 Registry。

        先保存到临时文件，成功后再替换正式文件，
        避免写入过程中损坏原 Registry。
        """
        if not isinstance(registry, dict):
            raise TypeError(
                "registry 必须是字典"
            )

        if not isinstance(
            registry.get("files"),
            dict,
        ):
            raise ValueError(
                "registry 中缺少合法的 files 字典"
            )

        with self._lock:
            temp_path = self.registry_path.with_name(
                f".{self.registry_path.name}."
                f"{uuid.uuid4().hex}.tmp"
            )

            try:
                with temp_path.open(
                    "w",
                    encoding="utf-8",
                ) as file:
                    json.dump(
                        registry,
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )

                    # 强制刷新 Python 缓冲区
                    file.flush()

                    # 尽量确保内容写入磁盘
                    os.fsync(file.fileno())

                # 原子替换正式 Registry
                os.replace(
                    temp_path,
                    self.registry_path,
                )

            except (OSError, TypeError) as error:
                raise RuntimeError(
                    f"Registry 保存失败：{error}"
                ) from error

            finally:
                # 如果替换前发生异常，清理临时文件
                if temp_path.exists():
                    temp_path.unlink()

    @staticmethod
    def calculate_file_hash(
        file_bytes: bytes,
    ) -> str:
        """
        根据文件二进制内容计算 SHA256。

        内容相同的文件，哈希值相同。
        """
        if not isinstance(
            file_bytes,
            bytes,
        ):
            raise TypeError(
                "file_bytes 必须是 bytes 类型"
            )

        if not file_bytes:
            raise ValueError(
                "文件内容不能为空"
            )

        return hashlib.sha256(
            file_bytes
        ).hexdigest()

    def exists_by_hash(
        self,
        file_hash: str,
    ) -> bool:
        """
        判断某个文件哈希是否已经登记。
        """
        return (
            self.get_by_hash(file_hash)
            is not None
        )

    def get_by_hash(
        self,
        file_hash: str,
    ) -> dict[str, Any] | None:
        """
        根据文件哈希获取文件信息。
        """
        if not file_hash:
            return None

        registry = self.load()

        for file_info in registry[
            "files"
        ].values():
            if (
                file_info.get("file_hash")
                == file_hash
            ):
                return file_info.copy()

        return None

    def add(
        self,
        file_info: dict[str, Any],
    ) -> dict[str, Any]:
        """
        向 Registry 中添加一个文件记录。
        """
        file_id = file_info.get("file_id")
        file_hash = file_info.get(
            "file_hash"
        )

        if not file_id:
            raise ValueError(
                "file_info 中缺少 file_id"
            )

        if not file_hash:
            raise ValueError(
                "file_info 中缺少 file_hash"
            )

        with self._lock:
            registry = self.load()
            files = registry["files"]

            # 检查 file_id 是否重复
            if file_id in files:
                raise ValueError(
                    f"file_id 已存在：{file_id}"
                )

            # 在当前加载的 Registry 中检查哈希
            # 不再重复调用 exists_by_hash()
            for existing_file in files.values():
                if (
                    existing_file.get(
                        "file_hash"
                    )
                    == file_hash
                ):
                    raise ValueError(
                        "该文件已经存在于知识库中"
                    )

            new_file_info = file_info.copy()

            # 设置默认管理字段
            new_file_info.setdefault(
                "status",
                "active",
            )

            new_file_info.setdefault(
                "version",
                1,
            )

            files[file_id] = new_file_info

            self.save(registry)

            return new_file_info.copy()

    def get_by_id(
        self,
        file_id: str,
    ) -> dict[str, Any] | None:
        """
        根据 file_id 获取文件信息。
        """
        if not file_id:
            return None

        registry = self.load()

        file_info = registry[
            "files"
        ].get(file_id)

        if file_info is None:
            return None

        return file_info.copy()

    def get_file(
        self,
        file_id: str,
    ) -> dict[str, Any] | None:
        """
        兼容原来的 get_file() 调用。

        新代码建议统一使用 get_by_id()。
        """
        return self.get_by_id(file_id)

    def list_files(
        self,
    ) -> list[dict[str, Any]]:
        """
        返回知识库中的全部文件。
        """
        registry = self.load()

        files = [
            file_info.copy()
            for file_info
            in registry["files"].values()
        ]

        # 按上传时间倒序排列
        return sorted(
            files,
            key=lambda item: item.get(
                "upload_time",
                "",
            ),
            reverse=True,
        )

    def update(
        self,
        file_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        更新指定文件的登记信息。

        可用于：
        - 更新 chunk_ids
        - 更新 chunk_count
        - 更新状态
        - 更新文件版本
        - 更新重新索引时间
        """
        if not file_id:
            raise ValueError(
                "file_id 不能为空"
            )

        if not isinstance(updates, dict):
            raise TypeError(
                "updates 必须是字典"
            )

        with self._lock:
            registry = self.load()
            files = registry["files"]

            if file_id not in files:
                raise KeyError(
                    f"Registry 中不存在文件：{file_id}"
                )

            current_file = files[file_id]

            # 不允许通过 update 修改文件唯一 ID
            safe_updates = updates.copy()
            safe_updates.pop(
                "file_id",
                None,
            )

            # 如果更新了 file_hash，
            # 检查是否与其他文件冲突
            new_file_hash = safe_updates.get(
                "file_hash"
            )

            if new_file_hash:
                for (
                    existing_file_id,
                    existing_file,
                ) in files.items():
                    if (
                        existing_file_id
                        != file_id
                        and existing_file.get(
                            "file_hash"
                        )
                        == new_file_hash
                    ):
                        raise ValueError(
                            "新的文件内容已经存在"
                        )

            current_file.update(
                safe_updates
            )

            # 始终确保 file_id 不发生变化
            current_file["file_id"] = file_id

            self.save(registry)

            return current_file.copy()

    def batch_update(
        self,
        updates: dict[
            str,
            dict[str, Any],
        ],
    ) -> None:
        """
        一次更新多个文件记录。

        索引全量重建时使用，
        避免每更新一个文件就保存一次 JSON。
        """
        if not isinstance(updates, dict):
            raise TypeError(
                "updates 必须是字典"
            )

        with self._lock:
            registry = self.load()
            files = registry["files"]

            # 先检查所有 file_id，避免更新到一半失败
            missing_file_ids = [
                file_id
                for file_id in updates
                if file_id not in files
            ]

            if missing_file_ids:
                raise KeyError(
                    "以下文件不存在："
                    + "、".join(missing_file_ids)
                )

            for (
                file_id,
                file_updates,
            ) in updates.items():
                safe_updates = (
                    file_updates.copy()
                )

                safe_updates.pop(
                    "file_id",
                    None,
                )

                files[file_id].update(
                    safe_updates
                )

                files[file_id][
                    "file_id"
                ] = file_id

            self.save(registry)

    def remove(
        self,
        file_id: str,
    ) -> dict[str, Any] | None:
        """
        从 Registry 中删除一个文件记录。

        注意：
        这里只删除 Registry 登记信息，
        不删除原始文件和 FAISS 向量。
        """
        if not file_id:
            raise ValueError(
                "file_id 不能为空"
            )

        with self._lock:
            registry = self.load()

            removed_file = registry[
                "files"
            ].pop(
                file_id,
                None,
            )

            if removed_file is None:
                return None

            self.save(registry)

            return removed_file.copy()