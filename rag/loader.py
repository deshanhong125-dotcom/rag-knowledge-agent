from langchain_community.document_loaders import PyPDFLoader,TextLoader,Docx2txtLoader
from pathlib import Path
def loader_document(file_path:str):
    """input: file path
    output: document"""
    #获取文件名字后缀
    suffix=Path(file_path).suffix.lower()
    if suffix==".pdf":
        loader=PyPDFLoader(file_path)
    elif suffix==".txt":
        loader=TextLoader(file_path=file_path,encoding="utf-8",autodetect_encoding=True)
    elif suffix == ".docx":
        loader = Docx2txtLoader(file_path)

    else:
        raise ValueError(f"不支持的文件格式：{suffix}")
    document=loader.load()
    return document

