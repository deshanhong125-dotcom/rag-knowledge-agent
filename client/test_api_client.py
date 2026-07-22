from client.api_client import ApiClient


def main():
    api_client=ApiClient()
    documents = api_client.get_documents()

    test_document = next(
        (
            document
            for document in documents
            if document["file_name"] == "test.txt"
        ),
        None,
    )

    if test_document is None:
        print("没有找到 test.txt")
        return

    file_id = test_document["file_id"]

    print("准备删除：", test_document["file_name"])
    print("文件ID：", file_id)

    delete_result = api_client.delete_document(
        file_id=file_id,
    )

    print("删除结果：", delete_result)

    documents_after = api_client.get_documents()

    exists_after = any(
        document["file_id"] == file_id
        for document in documents_after
    )

    print("删除后是否仍然存在：", exists_after)


if __name__ == "__main__":
    main()

