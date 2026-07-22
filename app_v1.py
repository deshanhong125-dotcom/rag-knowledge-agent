import streamlit as st
from rag.knowledge_base import save_uploaded_file,add_file_to_knowledge_base
from rag.loader import loader_document
from rag.splitter import split_document
from rag.retriever import retriever_documents
from rag.chain import *
from rag.chat_history_manager import ChatHistoryManager
history_manager = ChatHistoryManager()
from rag.chat_history_manager import (
    ChatHistoryManager,
)
from service.chat_service import (
    ChatService,
)
from langchain_community.chat_models import ChatTongyi

from config import CHAT_MODEL_NAME
from agent.langgraph_agent_service import (
    LangGraphAgentService,
)
from agent.tools import (
    search_knowledge_base,
    get_current_time,
    calculator,
)
@st.cache_resource
def get_chat_components():
    history_manager = (ChatHistoryManager())
    model=ChatTongyi(model=CHAT_MODEL_NAME)
    tools = [
        search_knowledge_base,
        get_current_time,
        calculator,
    ]
    agent_service = LangGraphAgentService(
        model=model,
        tools=tools,
    )
    chat_service = ChatService(history_manager=history_manager,agent_service=agent_service)

    return history_manager, chat_service

def render_sources(sources: list[dict]) -> None:
    """
    渲染一条助手消息对应的引用来源。
    """
    if not sources:
        return

    with st.expander(
        f"参考来源（{len(sources)}）"):
        for source_index, source in enumerate(sources,start=1,):
            file_name = source.get("file_name","未知文件", )
            page = source.get("page")
            chunk_index = source.get("index")
            chunk_content=source.get("chunk_content")
            if page is None:
                page_text = "页码未知"
            else:
                page_text = f"第 {page} 页"

            if chunk_index is None:
                chunk_text = "Chunk 编号未知"
            else:
                chunk_text = ( f"第 {chunk_index} 个 Chunk" )
            if chunk_content is None:
                chunk_content=(f"参考内容为{chunk_content}")

            st.markdown( f"**{source_index}. " f"{file_name}**")

            st.caption(f"{page_text} · {chunk_text} · {chunk_content}")

def render_message(message: dict,) -> None:
    """渲染单条聊天消息。接收message字典，这里是单条message，因此需要遍历"""
    role = message.get("role")#接收里面的role
    if role not in {"user","assistant",}:
        return

    content = message.get( "content","",)

    with st.chat_message(role):
        st.markdown(content)
    #如果是assistant就为这个聊天渲染一个markdown
        if role == "assistant":
            sources = message.get(
                "sources",
                [],
            )
            render_sources(sources)


st.title("RAG知识库检索问答")
#用state字典记录聊天会话历史
if "messages" not in st.session_state:
    st.session_state.messages = []
# 保存当前 Streamlit 会话中已经处理过的文件
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_files = set()

uploaded_file = st.file_uploader(
    "请上传你的文件",
    type=["pdf", "txt", "docx"],
)


if uploaded_file is not None:
    file_key = (uploaded_file.name,uploaded_file.size,)#获取文件的key

    st.write(f"当前文件：{uploaded_file.name}")
    st.write(f"文件大小：{uploaded_file.size} 字节")

    if file_key in st.session_state.uploaded_files:#判断是否在里面已经
        st.info("当前文件已经在本次会话中加入过知识库。")

    else:
        if st.button( "加入知识库",type="primary"

        ):
            try:
                with st.spinner("正在处理文件并构建索引..."):
                    result = add_file_to_knowledge_base(
                        file_name=uploaded_file.name,
                        file_bytes=uploaded_file.getvalue(),
                    )

                st.session_state.uploaded_files.add(file_key)

                st.success(result["message"])
                st.write(
                    f"原始 Document 数量："
                    f"{result['document_count']}"
                )
                st.write(
                    f"生成 Chunk 数量："
                    f"{result['chunk_count']}"
                )

            except Exception as error:
                st.error(f"文件入库失败：{error}")
else:
    st.info("请上传需要加入知识库的文件")

history_manager, chat_service = (
    get_chat_components()
)

# 1. 获取前端保存的当前会话ID
current_session_id = ( st.session_state.get("session_id"))
#  session_state没有时，从网址参数获取
if current_session_id is None:current_session_id = ( st.query_params.get("session_id") )

# 2. 确保会话真实存在
current_session_id = ( chat_service.ensure_session( current_session_id))

# 3. 将有效ID保存到前端
st.session_state.session_id = ( current_session_id)
#同时保存到网址参数
st.query_params["session_id"] = current_session_id
# 4. 清空当前会话,
if st.sidebar.button("清空当前对话", use_container_width=True,):
    history_manager.clear_messages(
        current_session_id
    )

    st.rerun()

if st.sidebar.button( "删除当前对话", use_container_width=True,):
   history_manager.delete_session(current_session_id)
   remain_session=history_manager.list_sessions()
   if remain_session :
       next_session_id = remain_session[0]["session_id"]
   else:
       next_session_id = history_manager.create_session()
   st.session_state.session_id = next_session_id
   st.query_params["session_id"] = next_session_id
   st.rerun()



#新建对话，如果按下这个按钮了，那么就执行这个操作
if st.sidebar.button( "新建对话",use_container_width=True,):
    #新建对话了，那么接下来就该创建id了
    new_session_id=history_manager.create_session()
    #将id保存到前端
    st.session_state.session_id = new_session_id
    st.query_params["session_id"] = new_session_id
    st.rerun()


# 5. 从后端读取并展示历史消息
messages = (history_manager.get_messages(current_session_id ) or [])

for message in messages:
    render_message(message)

# 6. 获取当前用户问题
question = st.chat_input("请输入问题")

# 7. 只有问题有效时才继续
if question is not None and question.strip():
    question = question.strip()

    # 先在当前页面显示用户消息
    user_message = {"role": "user", "content": question, }

    render_message(user_message)

    try:
        # 创建助手消息气泡
        with st.chat_message("assistant"):
            with st.spinner( "正在检索并生成答案..."):
                # ChatService负责：
                # 读取历史、调用RAG、保存用户和助手消息
                result = chat_service.chat(session_id=( current_session_id ),question=question, )#这里的结果由agent.run生成
            answer = result.get("answer","没有生成有效回答。",)

            sources = result.get("sources",[], )

            tool_calls=result.get("tool_calls",[], )
            st.markdown(answer)

            render_sources(sources)


        # 防止ChatService创建了新的会话ID
        st.session_state.session_id = ( result["session_id"] )

    except Exception as error:
        st.error(
            f"回答生成失败：{error}"
        )

#历史对话
st.sidebar.subheader("历史对话")
sessions= history_manager.list_sessions()#这里session就等于所有聊天的列表里面嵌套的字典
for session in sessions:
    session_id=session["session_id"]
    session_title=session.get("title","新对话")
    if st.sidebar.button(session_title, key=f"switch_session_{session_id}",use_container_width=True,):
        st.session_state.session_id = session_id
        st.query_params["session_id"] = session_id
        st.rerun()





