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

def repair_pptx(pptx_path):
    """
    Attempts to repair a broken PPTX file by fixing common corruptions like
    garbage bytes before the PK header or simple truncation.
    Returns True if repaired or valid, False otherwise.
    """
    try:
        import zipfile
        
        # Check if it's a valid zip first
        if zipfile.is_zipfile(pptx_path):
            try:
                with zipfile.ZipFile(pptx_path, 'r') as z:
                    if z.testzip() is not None:
                        print(f"Zip file {pptx_path} has corrupted contents")
                        return False
                return True # Already valid
            except zipfile.BadZipFile:
                pass # Proceed to repair
        
        print(f"Attempting to repair {pptx_path}...")
        
        # Read file content
        with open(pptx_path, 'rb') as f:
            content = f.read()
            
        # 1. Look for PK header
        pk_offset = content.find(b'PK\x03\x04')
        if pk_offset > 0:
            print(f"Found PK header at offset {pk_offset}, slicing...")
            content = content[pk_offset:]
            with open(pptx_path, 'wb') as f:
                f.write(content)
            
            if zipfile.is_zipfile(pptx_path):
                print(f"Repair successful: Sliced garbage bytes")
                return True
                
        # 2. Check for unexpected end of file (truncation) - harder to fix without recovery tools
        # But sometimes valid zips just have trailing garbage or are slightly off.
        
        # If we still can't open it as a zip, we can't do much without python-pptx
        if not zipfile.is_zipfile(pptx_path):
            print(f"Failed to repair {pptx_path}: Invalid zip structure")
            return False
            
        return True
    except Exception as e:
        print(f"Error repairing PPTX: {e}")
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
        # Try to repair and convert again
        try:
             if repair_pptx(pptx_path):
                 print(f"Retrying conversion for {pptx_path} after repair...")
                 presentation = Presentation()
                 presentation.LoadFromFile(pptx_path)
                 presentation.SaveToFile(pdf_path, FileFormat.PDF)
                 presentation.Dispose()
                 return True
        except Exception as repair_e:
             print(f"Repair and retry failed: {repair_e}")
             
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
