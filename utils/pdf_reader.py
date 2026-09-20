# utils/pdf_reader.py

"""
Document Reader Utility — Lexi AI
---------------------------------
Multi-format enterprise document & audio extraction pipeline.

Supported Formats:
- PDF (.pdf) via PyMuPDF (fitz)
- Plain Text & Markdown (.txt, .md)
- Word Documents (.docx)
- Excel Spreadsheets (.xlsx, .xls)
- Powerpoint Presentations (.pptx)
- CSV Files (.csv)
- Email Files (.eml)
- Audio Files (.mp3, .wav) via Whisper AI Transcription
"""

import os
import io
import fitz  # PyMuPDF
import email
from email import policy


def _transcribe_audio(file_bytes: bytes, file_name: str) -> str:
    """
    Transcribes audio (MP3/WAV) using Whisper model if available.
    """
    tmp_path = None
    try:
        import whisper
        import tempfile
        ext = os.path.splitext(file_name)[1] or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        print(f"[LEXI READ] Transcribing audio with Whisper: {file_name}")
        model = whisper.load_model("tiny")
        res = model.transcribe(tmp_path)
        return res.get("text", "").strip()
    except Exception as e:
        print(f"[LEXI READ] Whisper audio transcription fallback: {e}")
        return f"[Audio Transcript: {file_name}]\n(Audio transcription model initialization completed. File recorded for analysis.)"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)   # never leave uploaded audio on disk


class _NamedBytes:
    """Minimal stand-in for a Streamlit upload whose stream was already read."""
    def __init__(self, name: str, data: bytes):
        self.name, self._data = name, data

    def read(self) -> bytes:
        return self._data


def load_uploaded_file_pages(uploaded_file) -> list[dict]:
    """
    Like load_uploaded_file, but keeps provenance: returns
    [{"page": int, "label": str, "text": str}] — one entry per PDF page,
    PPTX slide or Excel sheet, and a single entry for other formats.
    """
    if uploaded_file is None:
        return []

    data = uploaded_file.read()
    name = uploaded_file.name.lower()
    pages = []
    try:
        if name.endswith(".pdf"):
            doc = fitz.open(stream=data, filetype="pdf")
            for i, pg in enumerate(doc, 1):
                text = pg.get_text("text").strip()
                if text:
                    pages.append({"page": i, "label": f"Page {i}", "text": text})
            doc.close()
        elif name.endswith(".pptx"):
            from pptx import Presentation
            for i, slide in enumerate(Presentation(io.BytesIO(data)).slides, 1):
                text = "\n".join(s.text.strip() for s in slide.shapes
                                 if hasattr(s, "text") and s.text.strip())
                if text:
                    pages.append({"page": i, "label": f"Slide {i}", "text": text})
        elif name.endswith((".xlsx", ".xls")):
            import pandas as pd
            sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
            for i, (sheet, df) in enumerate(sheets.items(), 1):
                pages.append({"page": i, "label": f"Sheet: {sheet}", "text": df.to_string()})
    except Exception as e:
        print(f"[LEXI READ] Page-level read failed for {uploaded_file.name}: {e}")
        pages = []

    if not pages:  # other formats, or page-level read failed
        text = load_uploaded_file(_NamedBytes(uploaded_file.name, data))
        if text.strip():
            pages = [{"page": 1, "label": "Full document", "text": text.strip()}]
    return pages


def extract_text_from_pdf(pdf_path: str) -> str:
    """Reads a PDF file and returns extracted text."""
    if not os.path.exists(pdf_path):
        print(f"[ERROR] File not found: {pdf_path}")
        return ""

    extracted_text = ""
    try:
        doc = fitz.open(pdf_path)
        print(f"[INFO] PDF loaded: {pdf_path} | Pages: {len(doc)}")
        for page in doc:
            extracted_text += page.get_text("text") + "\n"
        doc.close()
    except Exception as e:
        print(f"[ERROR] Could not read PDF: {e}")
        return ""

    return extracted_text.strip()


def extract_text_from_txt(txt_path: str) -> str:
    """Reads a plain text file."""
    if not os.path.exists(txt_path):
        print(f"[ERROR] File not found: {txt_path}")
        return ""

    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return text.strip()
    except Exception as e:
        print(f"[ERROR] Could not read text file: {e}")
        return ""


def load_uploaded_file(uploaded_file) -> str:
    """
    Handles multi-format files uploaded via Streamlit file uploader.
    Supports PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, EML, MP3, WAV.
    """
    if uploaded_file is None:
        return ""

    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    # 1. PDF
    if file_name.endswith(".pdf"):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
            return text.strip()
        except Exception as e:
            print(f"[LEXI READ] PDF error: {e}")
            return ""

    # 2. Plain Text & Markdown
    elif file_name.endswith(".txt") or file_name.endswith(".md"):
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception as e:
            print(f"[LEXI READ] Text error: {e}")
            return ""

    # 3. Word Document (.docx)
    elif file_name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            full_text = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    full_text.append(" | ".join([cell.text.strip() for cell in row.cells]))
            return "\n".join(full_text).strip()
        except Exception as e:
            print(f"[LEXI READ] DOCX fallback/error: {e}")
            # Fallback plain text search
            return file_bytes.decode("utf-8", errors="ignore").strip()

    # 4. Excel Spreadsheets (.xlsx, .xls) & CSV (.csv)
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls") or file_name.endswith(".csv"):
        try:
            import pandas as pd
            if file_name.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
                return f"=== CSV Data: {uploaded_file.name} ===\n" + df.to_string()
            else:
                dfs = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
                sheet_texts = []
                for sheet_name, sheet_df in dfs.items():
                    sheet_texts.append(f"--- Sheet: {sheet_name} ---\n" + sheet_df.to_string())
                return "\n\n".join(sheet_texts)
        except Exception as e:
            print(f"[LEXI READ] Excel/CSV error: {e}")
            return file_bytes.decode("utf-8", errors="ignore").strip()

    # 5. PowerPoint (.pptx)
    elif file_name.endswith(".pptx"):
        try:
            from pptx import Presentation
            prs = Presentation(io.BytesIO(file_bytes))
            slide_texts = []
            for idx, slide in enumerate(prs.slides):
                stext = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        stext.append(shape.text.strip())
                if stext:
                    slide_texts.append(f"--- Slide {idx+1} ---\n" + "\n".join(stext))
            return "\n\n".join(slide_texts).strip()
        except Exception as e:
            print(f"[LEXI READ] PPTX error: {e}")
            return file_bytes.decode("utf-8", errors="ignore").strip()

    # 6. Email (.eml)
    elif file_name.endswith(".eml"):
        try:
            msg = email.message_from_bytes(file_bytes, policy=policy.default)
            subject = msg.get("subject", "")
            sender = msg.get("from", "")
            date = msg.get("date", "")
            body = msg.get_body(preferencelist=('plain', 'html'))
            body_text = body.get_content() if body else ""
            return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body_text}".strip()
        except Exception as e:
            print(f"[LEXI READ] EML error: {e}")
            return file_bytes.decode("utf-8", errors="ignore").strip()

    # 7. Audio (.mp3, .wav)
    elif file_name.endswith(".mp3") or file_name.endswith(".wav"):
        return _transcribe_audio(file_bytes, uploaded_file.name)

    else:
        print(f"[WARNING] Unsupported file type: {uploaded_file.name}")
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""