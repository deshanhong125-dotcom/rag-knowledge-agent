import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from config import DATA_DIR


class ChatHistoryManager:

    def __init__(self,history_path: str | Path | None = None,):#传入属性只有一个，历史文件存储路径
        if history_path is None:
            history_path = (DATA_DIR / "chat_history.json")
        self.history_path = Path(history_path)
        self._lock = threading.RLock()

    @staticmethod
    def _empty_history() -> dict:
        """
        返回一个空的聊天历史数据结构。
        """
        return { "version": 1,
                "sessions": {},
        }

    def save(self, history_data: dict) -> None:
        """将历史聊天数据保存到本地 JSON 文件"""

        # 判断是否是字典
        if not isinstance(history_data, dict):
            raise TypeError("history_data 必须是字典")

        # 判断是否包含 sessions 字典
        if not isinstance(history_data.get("sessions"), dict):
            raise ValueError("history_data 中必须包含 sessions 字典")

        # 确保任何线程调用 save 时，同一时刻只有一个线程执行下面这段代码
        with self._lock:

            # 确保父目录存在
            self.history_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            # 创建临时文件路径
            temp_path = self.history_path.with_name(
                f".{self.history_path.name}.{uuid.uuid4().hex}.tmp"
            )

            try:
                # 写入临时文件
                with temp_path.open(
                        "w",
                        encoding="utf-8",
                ) as file:
                    json.dump(
                        history_data,
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )

                    # 将 Python 缓冲区的数据写入操作系统
                    file.flush()

                    # 将操作系统缓冲区的数据真正写入磁盘
                    os.fsync(file.fileno())

                # 用临时文件原子替换正式文件
                os.replace(
                    temp_path,
                    self.history_path,
                )

            finally:
                # 如果保存中途失败，清理临时文件
                if temp_path.exists():
                    temp_path.unlink()
    def load(self) ->dict:
        """从json文件中读取历史文件"""
        #核心就是 history_data=json.load(file)
        #return history_data
        with self._lock:
            # 文件不存在时，创建一个空历史文件
            if not self.history_path.exists():
                empty_data = self._empty_history()
                self.save(empty_data)
                return empty_data
        try:
            with self.history_path.open(
                    "r",
                    encoding="utf-8",
            ) as file:#把这个json文件给打开
                history_data = json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"聊天历史 JSON 格式错误：{error}"
            ) from error

        except OSError as error:
            raise OSError(
                f"聊天历史文件读取失败：{error}"
            ) from error

        if not isinstance(history_data, dict):
            raise ValueError(
                "聊天历史文件的根节点必须是字典"
            )

            # 兼容缺少 version 的旧数据
        if "version" not in history_data:
            history_data["version"] = 1

            # 兼容缺少 sessions 的旧数据
        if "sessions" not in history_data:
            history_data["sessions"] = {}

            # sessions 必须是字典
        if not isinstance(
                history_data["sessions"],
                dict,
        ):
            raise ValueError(
                "聊天历史中的 sessions 必须是字典"
            )

        return history_data

    def create_session(self) -> str:
        """
        创建一个新的聊天会话，并返回 session_id。
        """
        with self._lock:
            # 1. 读取已有历史数据,而且我们现在的history_data也是一样没有任何定义数据格式的
            history_data = self.load()

            # 2. 生成唯一会话 ID
            session_id = str(uuid.uuid4())

            # 3. 获取当前时间
            current_time = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            # 4. 创建新会话,这里中括号里面的session_id是占位符
            history_data["sessions"][session_id] = {
                "session_id": session_id,
                "title": "新对话",#默认是新对话
                "created_at": current_time,
                "updated_at": current_time,
                "messages": [],
               
            }
            # 5. 保存修改后的数据
            self.save(history_data)
            # 6. 返回新会话 ID
            return session_id

    def get_session( self,session_id: str, ) -> dict | None:
        """
        根据指定的session_id 查询指定会话。注意，我们只要求输出指定session_id的对话
        找到时返回会话字典；
        找不到时返回 None。
        """
        #接收变量之后，首先先判断变量的类型
        if not isinstance(session_id, str):
            raise TypeError("session_id必须是字符串类型")
        #去除id前后空格
        session_id=session_id.strip()
        #判断id是否为空
        if  not session_id :
            return None
        #取出聊天历史文件了
        history_data=self.load()
        session=history_data["sessions"].get(session_id)
        # 6. 没找到时返回 None
        if session is None:
            return None
            # 7. 检查会话数据格式
        if not isinstance(session, dict):
            raise ValueError("会话数据必须是字典" )
            # 8. 返回会话字典的副本
        return session.copy()

    def get_messages( self, session_id: str,) -> list[dict] | None:
        """
        根据 session_id 获取对应会话的消息列表。
        会话不存在时返回 None。
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        messages = session.get("messages")
        #只要获取到了新的内容，我们就需要检查一下类型是否适合
        if not isinstance(messages, list):
            raise ValueError( "会话中的 messages 必须是列表" )
        return messages.copy()

    def add_message(self,session_id: str,role: str, content: str,sources: list[dict] | None = None,) -> dict:
        """  向指定会话添加一条消息，
             并返回保存后的消息字典。
           """
        # 1. 检查消息角色
        if role not in { "user", "assistant", }:
            raise ValueError("role 必须是 user 或 assistant")
        # 2. 检查消息内容
        if not isinstance(content, str):
            raise TypeError("content 必须是字符串")
        #去除空白内容
        content = content.strip()

        if not content: raise ValueError( "消息内容不能为空" )

        # 3. 处理引用来源
        if sources is None:
            sources = []

        if not isinstance(sources, list):
            raise TypeError("sources 必须是列表" )
        with self._lock:
            # 4. 读取全部历史
            history_data = self.load()#本身这个load就是返回加载到内存上的history_data，后面所有的操作都是在内存上对他进行操作
            #5.找到指定对话
            session=history_data["sessions"].get(session_id)#先取出sessions对应的values，根据输入的session_id取出对应的session
            if session is None:
                raise KeyError(f"会话不存在：{session_id}")
            #检查消息列表
            messages=session["messages"]
            if not isinstance(messages, list):
                raise ValueError("会话中的 messages 必须是列表")
            # 判断以前是否保存过用户消息
            has_user_message = any(
                message.get("role") == "user"
                for message in messages
            )

            # 第一条用户消息作为标题
            if role == "user" and not has_user_message:
                max_title_length = 20
                session["title"] = content[:max_title_length]

                if len(content) > max_title_length:
                    session["title"] += "..."


            current_time = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            # 8. 创建消息字典
            message = {
                "role": role,
                "content": content,
                "created_at": current_time,
                "sources": sources,

            }
            # 9. 添加到消息列表
            messages.append(message)
            # 10. 更新会话的最后修改时间
            session["updated_at"] = current_time

            # 11. 保存全部历史数据
            self.save(history_data)

            # 12. 返回刚保存的消息
            return message.copy()

    def clear_messages( self, session_id: str, ) -> int:
        """
        清空指定会话的全部消息，返回被清除的消息数量。这里只是清空message列表
        """
        #先拿到消息
        with self._lock:
            history_data = self.load()
            session = history_data["sessions"].get(session_id)#我们的session就是单个id的会话记录，包含标题，时间，内容等信息
            if session is None:
                raise KeyError(
                    f"会话不存在：{session_id}"
                )
            messages = session.get("messages")
            if not isinstance(messages, list):
                raise ValueError("会话中的 messages 必须是列表")
            #记录原来消息的数量
            deleted_count = len(messages)
            #清空指定的消息列表，清空方法直接赋为空列表即可
            session["messages"]=[]
            # 6. 更新最后修改时间
            session["updated_at"] = (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
            # 7. 保存到硬盘
            self.save(history_data)

            # 8. 返回清除的消息数量
            return deleted_count

    def list_sessions(self) -> list[dict]:
        """用于展示所有聊天会话"""
        chat_list=[]
        history_data = self.load()
        sessions=history_data["sessions"]
        if not isinstance(sessions, dict):
            raise ValueError("聊天列表应该是字典类型")
        for session_id,session in sessions.items():
            if not isinstance(session, dict):
                continue
            messages = session.get("messages",[],)
            if not isinstance(messages, list):
                messages = []
            chat_dict={
                "session_id": session_id,
                "title": session.get("title","新对话"),
                "created_at":session.get("created_at"),
                "updated_at": session.get("updated_at", ),
                "message_count": len(messages),
            }
            chat_list.append(chat_dict)
            chat_list.sort(
                key=lambda chat: (
                        chat.get("updated_at") or ""
                ),
                reverse=True,
            )
        return chat_list

    def delete_session(
            self,
            session_id: str,
    ) -> dict:
        """删除指定会话，并返回被删除的会话数据。"""

        if not isinstance(session_id, str):
            raise ValueError("session_id 必须是字符串")

        session_id = session_id.strip()

        if not session_id:
            raise ValueError("session_id 不能为空")

        with self._lock:
            history_data = self.load()
            sessions = history_data.get("sessions")

            if not isinstance(sessions, dict):
                raise ValueError(
                    "历史数据中的 sessions 格式错误"
                )

            deleted_session = sessions.pop(
                session_id,
                None,
            )

            if deleted_session is None:
                raise KeyError(
                    f"会话不存在：{session_id}"
                )

            self.save(history_data)

        return deleted_session








