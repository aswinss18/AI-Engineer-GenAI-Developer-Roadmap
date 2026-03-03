def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    """
    Improved paragraph-aware text chunker with overlap.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    # Split by double newlines to preserve section structure
    sections = text.split("\n\n")
    
    chunks = []
    current_chunk = ""
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # If adding this section would exceed chunk_size
        if len(current_chunk) + len(section) + 2 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                
                # Create overlap by taking last few complete words
                words = current_chunk.split()
                overlap_text = " ".join(words[-30:]) if len(words) > 30 else current_chunk
                current_chunk = overlap_text + "\n\n" + section
            else:
                # Section itself is larger than chunk_size, add it anyway
                current_chunk = section
        else:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
