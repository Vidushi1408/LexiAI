# webapp/uploads.py
"""Adapts a Werkzeug FileStorage (Flask's request.files) to the small .name/.read() interface
that utils.pdf_reader and utils.upload_guard already expect (they were written against Streamlit's
UploadedFile, which has the same shape)."""


class FlaskUpload:
    def __init__(self, storage) -> None:
        self.name = storage.filename or "unnamed"
        self._data = storage.read()

    def read(self) -> bytes:
        return self._data

    def getvalue(self) -> bytes:
        return self._data
