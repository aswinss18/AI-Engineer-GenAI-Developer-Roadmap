from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(pages_data):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks_with_metadata = []
    chunk_index = 0  # Global chunk index to ensure order matches FAISS index

    for page_data in pages_data:
        text_chunks = splitter.split_text(page_data["text"])

        for chunk in text_chunks:
            chunks_with_metadata.append({
                "text": chunk,
                "page": page_data["page"],
                "doc": page_data["doc"],
                "chunk_index": chunk_index  # Add chunk index for FAISS order consistency
            })
            chunk_index += 1

    return chunks_with_metadata
