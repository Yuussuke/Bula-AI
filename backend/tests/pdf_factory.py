import fitz


def build_pdf_bytes(text: str = "Bula de teste") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content
