def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150):
    """
    Paragraph-aware text chunker with overlap.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    paragraphs = text.split("\n")
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap:] + para + "\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
