from pypdf import PdfReader


def extract_text_from_pdf(file):
    reader = PdfReader(file)

    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    return text, len(reader.pages)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks