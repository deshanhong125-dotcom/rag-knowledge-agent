from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent


# 数据目录
DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR = DATA_DIR / "uploads"

FAISS_DIR = DATA_DIR / "faiss_db"


# 文档切分配置
CHUNK_SIZE = 800

CHUNK_OVERLAP = 100


# Embedding 模型配置
EMBEDDING_MODEL_NAME = "text-embedding-v4"


# 自动创建目录
UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FAISS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

# 每次检索返回最相关的 Chunk 数量
RETRIEVAL_K = 3
FETCH_K=10
LAMBDA_MULT=0.5


#大模型配置
CHAT_MODEL_NAME = "qwen3-max"

#备份目录
BACKUP_DIR = DATA_DIR / "backups"
TRASH_DIR = DATA_DIR / "trash"

