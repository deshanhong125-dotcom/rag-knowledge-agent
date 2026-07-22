from config import FETCH_K, LAMBDA_MULT, RETRIEVAL_K
from rag.knowledge_base import load_vectorstore, vectorstore_exists


def retriever_documents(question:str):
    """
       输入：用户问题
       输出：检索到的 Document 列表

       如果知识库不存在，返回空列表。
       """
    if not question.strip():
        return []
    if not vectorstore_exists():
        return []
    vectorstore=load_vectorstore()#接收这个对象之后，就可以继续使用里面的方法了
    #用接收对象里的查询，最终返回一个documents
    documents=vectorstore.similarity_search(
        question,
        RETRIEVAL_K,
        fetch_k=FETCH_K,
        lambda_mult=LAMBDA_MULT,

    )
    return documents
