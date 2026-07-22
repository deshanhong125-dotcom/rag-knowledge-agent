import os

from dotenv import load_dotenv
from langchain_community.embeddings import DashScopeEmbeddings

from config import EMBEDDING_MODEL_NAME


# 读取项目中的 .env 文件
load_dotenv()


def get_embedding_model() -> DashScopeEmbeddings:
    """
    创建并返回 Embedding 模型。

    该模型同时用于：
    1. 将文档 Chunk 转换成向量；
    2. 将用户问题转换成向量。
    """

    embedding_model = DashScopeEmbeddings(
        model=EMBEDDING_MODEL_NAME,
    )

    return embedding_model



