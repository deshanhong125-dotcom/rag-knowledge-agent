import requests
class ApiClient:
    "负责向FastAPI后端发发送HTTP请求"
    def __init__(
            self,
            base_url:str="http://127.0.0.1:8000",
    ):
        self.base_url = base_url.rstrip("/")
        self.session=requests.Session()
    def health_check(self)->dict:
        """检查FastAPI后端是否正常运行"""
        try:
            response=self.session.get(url=f"{self.base_url}/health",timeout=5,)
            response.raise_for_status()
            return response.json()#返回接受的json结构
        except requests.RequestException as error:
            raise RuntimeError(
                f"无法链接FastAPI后端:{error}"
            ) from error

    def chat(
            self,
            question: str,
            session_id: str | None = None,
    ) -> dict:
        """向 FastAPI 后端发送聊天请求。"""
        question = question.strip()

        if not question:
            raise ValueError("问题不能为空")
        #构建携带的数据
        payload={
            "session_id": session_id,
            "question": question,
        }
        try:
            response=self.session.post(url=f"{self.base_url}/chat",json=payload,timeout=120,)
            response.raise_for_status()#检查请求是否异常，如果失败就抛出异常
            return response.json()
        except requests.RequestException as error:
            raise RuntimeError(
                f"聊天请求失败：{error}"
            ) from error

    def get_sessions(self)->dict:
        """获取全部聊天会话摘要"""
        try:
            response=self.session.get(url=f"{self.base_url}/sessions",timeout=10,)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            raise RuntimeError(
                f"获取会话列表失败：{error}"
            ) from error

    def get_session_messages(
            self,
            session_id: str,
    ) -> list[dict]:
        """获取指定会话的全部历史消息。"""

        if not isinstance(session_id, str):
            raise TypeError("session_id 必须是字符串")

        session_id = session_id.strip()

        if not session_id:
            raise ValueError("session_id 不能为空")

        try:
            response = self.session.get(
                url=(
                    f"{self.base_url}/sessions/"
                    f"{session_id}/messages"
                ),
                timeout=10,
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(
                f"获取会话消息失败：{error}"
            ) from error

    def clear_messages(self,session_id: str)->dict:
        """清空指定会话中的messages,使其变为[]"""
        if not isinstance(session_id, str):
            raise TypeError("session_id必须是字符串类型")
        session_id=session_id.strip()
        if not session_id:
            raise TypeError("输入的session_id不能为空")
        try:
            response=self.session.delete(url=f"{self.base_url}/sessions/{session_id}/messages",timeout=10,)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            raise RuntimeError(
                f"清空会话消息失败：{error}"
            ) from error

    def delete_session(self,session_id: str)->dict:
        """删除指定对话的整个session"""
        if not isinstance(session_id, str):
            raise TypeError("session_id必须是字符串")
        session_id=session_id.strip()
        if not session_id:
            raise TypeError("输入的session_id不能为空")
        try:
           response=self.session.delete(url=f"{self.base_url}/sessions/{session_id}",timeout=10,)
           response.raise_for_status()
           return response.json()
        except requests.RequestException as error:
            raise RuntimeError(
                f"删除会话失败：{error}"
            ) from error

    def get_documents(self)->dict:
        """获取知识库的全部文件，最终返回list[DocumentSummary]"""
        try:
            response = self.session.get(
                url=f"{self.base_url}/documents",
                timeout=10,
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(
                f"获取知识库文件列表失败：{error}"
            ) from error

    def upload_document(
            self,
            file_name: str,
            file_bytes: bytes,
    ) -> dict:
        """上传文件到知识库。"""

        if not isinstance(file_name, str):
            raise TypeError("file_name 必须是字符串")

        file_name = file_name.strip()

        if not file_name:
            raise ValueError("文件名不能为空")

        if not isinstance(file_bytes, bytes):
            raise TypeError("file_bytes 必须是 bytes")

        if not file_bytes:
            raise ValueError("文件内容不能为空")

        files = {
            "file": (
                file_name,
                file_bytes,
            )
        }

        try:
            response = self.session.post(
                url=f"{self.base_url}/documents",
                files=files,
                timeout=300,
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(
                f"上传知识库文件失败：{error}"
            ) from error

    def delete_document(self,file_id: str)->dict:
        """用于删除指定file_id的知识库文件"""
        if not isinstance(file_id, str):
            raise TypeError("file_id 必须是字符串")

        file_id = file_id.strip()

        if not file_id:
            raise ValueError("file_id 不能为空")

        try:
            response = self.session.delete(
                url=(
                    f"{self.base_url}/documents/"
                    f"{file_id}"
                ),
                timeout=120,
            )

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(
                f"删除知识库文件失败：{error}"
            ) from error
