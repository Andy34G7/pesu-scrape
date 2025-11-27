import os
import requests
from pypdf import PdfWriter
import img2pdf
from spire.presentation import Presentation, FileFormat

def download_file(url, session, output_path):
    response = session.get(url, stream=True)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    return False

def convert_pptx_to_pdf(pptx_path, pdf_path):
    try:
        presentation = Presentation()
        presentation.LoadFromFile(pptx_path)
        presentation.SaveToFile(pdf_path, FileFormat.PDF)
        presentation.Dispose()
        return True
    except Exception as e:
        print(f"Error converting PPTX: {e}")
        return False

from spire.doc import Document, FileFormat as DocFileFormat

def convert_docx_to_pdf(docx_path, pdf_path):
    try:
        document = Document()
        document.LoadFromFile(docx_path)
        document.SaveToFile(pdf_path, DocFileFormat.PDF)
        document.Close()
        return True
    except Exception as e:
        print(f"Error converting DOCX: {e}")
        return False

def merge_pdfs(pdf_paths, output_path):
    merger = PdfWriter()
    for pdf in pdf_paths:
        try:
            merger.append(pdf)
        except Exception as e:
            print(f"Error appending PDF {pdf}: {e}")
    
    merger.write(output_path)
    merger.close()
