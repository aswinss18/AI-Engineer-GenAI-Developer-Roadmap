from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(pages_data):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    chunks_with_metadata = []
    
    for page_data in pages_data:
        text_chunks = splitter.split_text(page_data["text"])
        
        for chunk in text_chunks:
            chunks_with_metadata.append({
                "text": chunk,
                "page": page_data["page"],
                "doc": page_data["doc"]
            })
    
    return chunks_with_metadata