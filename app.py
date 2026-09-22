# app.py
"""
Lexi AI entrypoint.

Dev:  python app.py            (Flask's built-in server, debug reload)
Prod: gunicorn -w 2 -b 0.0.0.0:8000 --timeout 120 app:app
"""
import os

from webapp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8000)), debug=True)
