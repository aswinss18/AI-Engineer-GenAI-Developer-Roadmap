from pypdf import PdfReader

def load_pdf(file_path):
    reader = PdfReader(file_path)

    pages_data = []

    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text.strip():  # Only add pages with content
            pages_data.append({
                "text": text,
                "page": page_num,
                "doc": file_path.split("/")[-1]  # Extract filename
            })

    return pages_data
