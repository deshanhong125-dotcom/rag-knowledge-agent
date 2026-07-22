import streamlit as st

from client.api_client import ApiClient
import os

# set_page_config 必须在其他 Streamlit 页面命令之前执行。
st.set_page_config(
    page_title="企业知识库 Agent 助手",
    page_icon="🤖",
    layout="wide",
)

# ============================================================
# API 客户端与页面状态
# ============================================================


@st.cache_resource
def get_api_client() -> ApiClient:
    """创建并复用 ApiClient，避免页面每次重跑都重新创建客户端。尝试读取，如果没有读取到，那么就使用默认值"""
    base_url = os.getenv(
        "API_BASE_URL",
        "http://127.0.0.1:8000",
    )

    return ApiClient(base_url=base_url)


def initialize_session_state() -> None:
    """初始化当前会话、删除确认和操作提示等前端状态。"""
    default_states = {
        "session_id": None,
        "pending_delete_session_id": None,
        "session_notice": None,
        "pending_delete_file_id": None,
        "knowledge_base_notice": None,
    }

    for key, default_value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def select_session(session_id: str | None) -> None:
    """切换当前会话；None 表示进入尚未创建的新对话。"""
    st.session_state.session_id = session_id

    # 切换会话时取消尚未确认的会话删除操作。
    st.session_state.pending_delete_session_id = None


def find_session(
    sessions: list[dict],
    session_id: str | None,
) -> dict | None:
    """根据 session_id 在会话列表中查找指定会话。"""
    if session_id is None:
        return None

    return next(
        (
            session
            for session in sessions
            if session.get("session_id") == session_id
        ),
        None,
    )


# ============================================================
# 聊天消息与引用来源
# ============================================================


def render_sources(sources: list[dict]) -> None:
    """渲染一条助手消息所引用的知识库来源。"""
    if not sources:
        return

    with st.expander(f"参考来源（{len(sources)}）"):
        for source_index, source in enumerate(sources, start=1):
            file_name = source.get("file_name", "未知文件")
            page = source.get("page")
            chunk_index = source.get("index")
            chunk_content = source.get("chunk_content")

            page_text = (
                f"第 {page} 页"
                if page is not None
                else "页码未知"
            )
            chunk_text = (
                f"第 {chunk_index} 个 Chunk"
                if chunk_index is not None
                else "Chunk 编号未知"
            )

            st.markdown(f"**{source_index}. {file_name}**")
            st.caption(f"{page_text} · {chunk_text}")

            # 只有后端确实返回了 Chunk 内容时才展示，避免显示 None。
            if chunk_content:
                st.markdown(f"> {chunk_content}")


def render_message(message: dict) -> None:
    """渲染一条用户消息或助手消息。"""
    role = message.get("role")

    # 忽略 system、tool 等不需要直接展示在聊天区的消息。
    if role not in {"user", "assistant"}:
        return

    content = message.get("content") or ""

    with st.chat_message(role):
        st.markdown(content)

        if role == "assistant":
            render_sources(message.get("sources") or [])


# ============================================================
# 知识库管理
# ============================================================


def render_document_uploader(api_client: ApiClient) -> None:
    """渲染文件上传控件，并把文件发送给 FastAPI 后端。"""
    uploaded_file = st.file_uploader(
        "上传知识库文件",
        type=["pdf", "txt", "docx"],
        key="knowledge_file",
    )

    upload_clicked = st.button(
        "上传并加入知识库",
        disabled=uploaded_file is None,
        use_container_width=True,
    )

    if not upload_clicked or uploaded_file is None:
        return

    try:
        with st.spinner("正在解析并写入知识库..."):
            result = api_client.upload_document(
                file_name=uploaded_file.name,
                file_bytes=uploaded_file.getvalue(),
            )

        if result.get("duplicate"):
            st.warning("该文件已经存在于知识库中")
        else:
            file_name = result.get(
                "file_name",
                uploaded_file.name,
            )
            chunk_count = result.get("chunk_count", 0)
            st.success(
                f"{file_name} 上传成功，共生成 "
                f"{chunk_count} 个 Chunk"
            )

    except (ValueError, RuntimeError) as error:
        st.error(f"文件上传失败：{error}")


def render_document_delete_confirmation(
    api_client: ApiClient,
    documents: list[dict],
) -> None:
    """对待删除文件进行二次确认，并执行删除请求。"""
    pending_file_id = st.session_state.pending_delete_file_id#等待处理的文件id

    if pending_file_id is None:
        return

    pending_document = next(
        (
            document
            for document in documents
            if document.get("file_id") == pending_file_id
        ),
        None,
    )#这里的next表示为拿到第一个满足条件的对象

    # 文件可能已经被其他请求删除，此时清理失效的待删除状态。
    if pending_document is None:
        st.session_state.pending_delete_file_id = None
        return

    pending_file_name = pending_document.get(
        "file_name",
        "未知文件",
    )

    st.warning(f"确定删除「{pending_file_name}」吗？")
    confirm_column, cancel_column = st.columns(2)

    with confirm_column:
        if st.button(
            "确认删除",
            key="confirm_document_delete",
            type="primary",
            use_container_width=True,
        ):
            try:
                with st.spinner("正在删除文件..."):
                    result = api_client.delete_document(
                        file_id=pending_file_id,
                    )

                st.session_state.pending_delete_file_id = None
                st.session_state.knowledge_base_notice = result.get(
                    "message",
                    f"{pending_file_name} 删除成功",
                )

                # 删除后重新获取文件列表，避免页面继续展示旧数据。
                st.rerun()

            except (ValueError, RuntimeError) as error:
                st.error(f"删除文件失败：{error}")

    with cancel_column:
        if st.button(
            "取消",
            key="cancel_document_delete",
            use_container_width=True,
        ):
            st.session_state.pending_delete_file_id = None
            st.rerun()


def render_knowledge_base(api_client: ApiClient) -> None:
    """渲染知识库的上传、文件列表和删除功能。"""
    st.subheader("知识库管理")

    notice = st.session_state.knowledge_base_notice
    if notice:
        st.success(notice)
        # 操作提示只展示一次。
        st.session_state.knowledge_base_notice = None

    render_document_uploader(api_client)

    st.divider()
    st.markdown("#### 已有文件")

    try:
        documents = api_client.get_documents()
    except RuntimeError as error:
        st.error(f"获取知识库文件失败：{error}")
        return

    if not documents:
        st.session_state.pending_delete_file_id = None
        st.info("知识库中暂时没有文件")
        return

    for document_index, document in enumerate(documents):
        file_id = document.get("file_id")
        file_name = document.get("file_name", "未知文件")
        chunk_count = document.get("chunk_count", 0)

        file_column, delete_column = st.columns([3, 1])

        with file_column:
            st.markdown(f"**{file_name}**")
            st.caption(f"共 {chunk_count} 个 Chunk")

        with delete_column:
            if st.button(
                "删除",
                key=f"delete_document_{file_id or document_index}",
                disabled=not file_id,
                use_container_width=True,
            ):
                # 第一次点击只记录目标文件，实际删除需要再次确认。
                st.session_state.pending_delete_file_id = file_id

    render_document_delete_confirmation(
        api_client=api_client,
        documents=documents,
    )


# ============================================================
# 会话管理
# ============================================================


def render_session_delete_confirmation(
    api_client: ApiClient,
    sessions: list[dict],
) -> None:
    """对待删除会话进行二次确认，并执行删除请求。"""
    pending_session_id = (
        st.session_state.pending_delete_session_id
    )

    if pending_session_id is None:
        return

    pending_session = find_session(
        sessions=sessions,
        session_id=pending_session_id,
    )

    if pending_session is None:
        st.session_state.pending_delete_session_id = None
        return

    pending_title = pending_session.get("title", "新对话")

    st.warning(f"确定删除会话「{pending_title}」吗？")
    confirm_column, cancel_column = st.columns(2)

    with confirm_column:
        if st.button(
            "确认删除",
            key="confirm_session_delete",
            type="primary",
            use_container_width=True,
        ):
            try:
                with st.spinner("正在删除会话..."):
                    result = api_client.delete_session(
                        session_id=pending_session_id,
                    )

                # 如果删除的是当前会话，删除后回到新对话页面。
                if st.session_state.session_id == pending_session_id:
                    st.session_state.session_id = None

                st.session_state.pending_delete_session_id = None
                st.session_state.session_notice = result.get(
                    "message",
                    f"会话「{pending_title}」已删除",
                )
                st.rerun()

            except (ValueError, RuntimeError) as error:
                st.error(f"删除会话失败：{error}")

    with cancel_column:
        if st.button(
            "取消",
            key="cancel_session_delete",
            use_container_width=True,
        ):
            st.session_state.pending_delete_session_id = None
            st.rerun()


def render_session_management(
    api_client: ApiClient,
    sessions: list[dict],
) -> None:
    """渲染新建对话、历史会话列表和会话删除功能。"""
    st.header("对话管理")

    notice = st.session_state.session_notice
    if notice:
        st.success(notice)
        st.session_state.session_notice = None

    st.button(
        "＋ 新建对话",
        on_click=select_session,
        args=(None,),
        use_container_width=True,
    )

    st.divider()
    st.subheader("历史会话")

    if not sessions:
        st.info("暂无历史会话")

    for session in sessions:
        session_id = session.get("session_id")

        # 缺少 session_id 的异常数据无法切换或删除，直接跳过。
        if not session_id:
            continue

        title = session.get("title", "新对话")
        message_count = session.get("message_count", 0)
        is_current = session_id == st.session_state.session_id

        session_column, delete_column = st.columns([4, 1])

        with session_column:
            st.button(
                label=f"{title}（{message_count} 条）",
                key=f"session_{session_id}",
                type="primary" if is_current else "secondary",
                on_click=select_session,
                args=(session_id,),
                use_container_width=True,
            )

        with delete_column:
            if st.button(
                "🗑️",
                key=f"delete_session_{session_id}",
                help=f"删除会话：{title}",
                use_container_width=True,
            ):
                # 第一次点击只进入待确认状态。
                st.session_state.pending_delete_session_id = session_id

    render_session_delete_confirmation(
        api_client=api_client,
        sessions=sessions,
    )


def render_sidebar(
    api_client: ApiClient,
    sessions: list[dict],
) -> None:
    """渲染侧边栏中的会话管理和知识库管理。"""
    with st.sidebar:
        render_session_management(
            api_client=api_client,
            sessions=sessions,
        )

        st.divider()
        render_knowledge_base(api_client)


# ============================================================
# 主聊天区域
# ============================================================


def load_current_messages(
    api_client: ApiClient,
    sessions: list[dict],
) -> tuple[str | None, list[dict]]:
    """确定当前会话，并从后端读取该会话的历史消息。"""
    current_session_id = st.session_state.session_id

    if current_session_id is None:
        st.subheader("新对话")
        st.caption("请输入问题开始新的对话")
        return None, []

    selected_session = find_session(
        sessions=sessions,
        session_id=current_session_id,
    )

    if selected_session is None:
        st.warning("当前会话不存在，已切换到新对话")
        st.session_state.session_id = None
        return None, []

    st.subheader(selected_session.get("title", "新对话"))

    try:
        messages = api_client.get_session_messages(
            session_id=current_session_id,
        )
    except RuntimeError as error:
        st.error(f"获取历史消息失败：{error}")
        messages = []

    return current_session_id, messages


def render_chat_area(
    api_client: ApiClient,
    sessions: list[dict],
) -> None:
    """渲染历史消息、聊天输入框，并把新问题发送给后端。"""
    current_session_id, messages = load_current_messages(
        api_client=api_client,
        sessions=sessions,
    )

    # 后端历史记录是唯一数据源，前端只负责读取和展示。
    for message in messages:
        render_message(message)

    question = st.chat_input("请输入问题")
    if question is None:
        return

    question = question.strip()
    if not question:
        return

    # 先展示用户刚提交的问题，减少等待期间的视觉延迟。
    with st.chat_message("user"):
        st.markdown(question)

    try:
        with st.spinner("Agent 正在思考..."):
            result = api_client.chat(
                question=question,
                session_id=current_session_id,
            )

        new_session_id = result.get("session_id")
        if not new_session_id:
            raise RuntimeError("后端响应中缺少 session_id")

        # 新对话第一次提问后，保存后端创建的正式 session_id。
        st.session_state.session_id = new_session_id

        # 重新运行后，从后端获取并展示最新的完整消息列表。
        st.rerun()

    except (ValueError, RuntimeError) as error:
        st.error(f"回答生成失败：{error}")


# ============================================================
# 页面入口
# ============================================================


def main() -> None:
    """启动 Streamlit 页面。"""
    initialize_session_state()
    api_client = get_api_client()

    st.title("企业知识库 Agent 助手")
    st.caption("基于 FastAPI、LangGraph 和 RAG 的知识库问答系统")

    try:
        sessions = api_client.get_sessions()
    except RuntimeError as error:
        st.error(f"无法连接 FastAPI 后端：{error}")
        st.info("请确认 FastAPI 已经在 http://127.0.0.1:8000 运行")
        st.stop()

    render_sidebar(
        api_client=api_client,
        sessions=sessions,
    )
    render_chat_area(
        api_client=api_client,
        sessions=sessions,
    )


if __name__ == "__main__":
    main()

