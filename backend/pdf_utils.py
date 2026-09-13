import os
import sys
import logging
from pypdf import PdfWriter
import img2pdf

# Ensure proper globalization for Spire library on Linux
os.environ.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")

logger = logging.getLogger("pdf_utils")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def convert_image_to_pdf(image_path, pdf_path):
    try:
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_path))
        return True
    except Exception as e:
        logger.error(f"Error converting image to PDF: {e}")
        return False


def download_file(url, session, output_path):
    try:
        response = session.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        return False


def repair_pptx(pptx_path):
    try:
        import zipfile
        if zipfile.is_zipfile(pptx_path):
            try:
                with zipfile.ZipFile(pptx_path, 'r') as z:
                    if z.testzip() is not None:
                        logger.warning(f"Zip file {pptx_path} has corrupted contents")
                        return False
                return True
            except zipfile.BadZipFile:
                pass
        
        logger.info(f"Attempting to repair {pptx_path}...")
        with open(pptx_path, 'rb') as f:
            content = f.read()
            
        pk_offset = content.find(b'PK\x03\x04')
        if pk_offset > 0:
            content = content[pk_offset:]
            with open(pptx_path, 'wb') as f:
                f.write(content)
            
            if zipfile.is_zipfile(pptx_path):
                logger.info("Repair successful: Sliced garbage bytes")
                return True
                
        if not zipfile.is_zipfile(pptx_path):
            logger.warning(f"Failed to repair {pptx_path}: Invalid zip structure")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error repairing PPTX: {e}")
        return False


def convert_pptx_to_pdf(pptx_path, pdf_path):
    try:
        from spire.presentation import Presentation, FileFormat
        presentation = Presentation()
        presentation.LoadFromFile(pptx_path)
        presentation.SaveToFile(pdf_path, FileFormat.PDF)
        presentation.Dispose()
        return True
    except Exception as e:
        logger.warning(f"Spire PPTX conversion failed: {e}. Retrying with repair...")
        try:
            if repair_pptx(pptx_path):
                from spire.presentation import Presentation, FileFormat
                presentation = Presentation()
                presentation.LoadFromFile(pptx_path)
                presentation.SaveToFile(pdf_path, FileFormat.PDF)
                presentation.Dispose()
                return True
        except Exception as repair_e:
            logger.error(f"Repair and retry failed: {repair_e}")
            
        return False


def convert_docx_to_pdf(docx_path, pdf_path):
    try:
        from spire.doc import Document, FileFormat as DocFileFormat
        doc = Document()
        doc.LoadFromFile(docx_path)
        doc.SaveToFile(pdf_path, DocFileFormat.PDF)
        doc.Dispose()
        return True
    except Exception as e:
        logger.error(f"Error converting DOCX {docx_path} to PDF: {e}")
        return False


def convert_to_pdf(source_path, pdf_path):
    ext = os.path.splitext(source_path)[1].lower()
    if ext in ['.png', '.jpg', '.jpeg']:
        return convert_image_to_pdf(source_path, pdf_path)
    elif ext in ['.ppt', '.pptx']:
        return convert_pptx_to_pdf(source_path, pdf_path)
    elif ext in ['.doc', '.docx']:
        return convert_docx_to_pdf(source_path, pdf_path)
    elif ext == '.pdf':
        return True
    else:
        logger.warning(f"Unsupported format for PDF conversion: {ext}")
        return False


def merge_pdfs(pdf_paths, output_path):
    merger = PdfWriter()
    try:
        for pdf in pdf_paths:
            if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                merger.append(pdf)
            else:
                logger.warning(f"Skipping missing or empty PDF for merge: {pdf}")
        with open(output_path, "wb") as f_out:
            merger.write(f_out)
        merger.close()
        return True
    except Exception as e:
        logger.error(f"Error merging PDFs: {e}")
        return False
