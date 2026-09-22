# webapp/__init__.py
"""Flask application factory for Lexi AI."""
import logging
import os
import sys
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from flask import Flask, render_template

from config import settings
from logging_setup import configure_logging

log = logging.getLogger("lexi.web")


@lru_cache(maxsize=1)
def _ensure_nltk_data() -> None:
    import nltk
    for pkg, path in [("punkt", "tokenizers/punkt"), ("punkt_tab", "tokenizers/punkt_tab"),
                      ("stopwords", "corpora/stopwords"), ("wordnet", "corpora/wordnet"),
                      ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger")]:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)


def create_app() -> Flask:
    configure_logging()
    _ensure_nltk_data()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.session_cookie_secure,
        MAX_CONTENT_LENGTH=max(settings.max_upload_mb, settings.max_audio_mb) * 1024 * 1024 * 20,  # allow several files
    )

    from webapp import security
    security.init_app(app)

    from webapp.markdown_utils import render_markdown
    app.jinja_env.filters["markdown"] = render_markdown

    from webapp.blueprints.auth import bp as auth_bp
    from webapp.blueprints.features import bp as features_bp
    from webapp.blueprints.kb import bp as kb_bp
    from webapp.blueprints.main import bp as main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(kb_bp)
    app.register_blueprint(features_bp)

    @app.context_processor
    def _inject_llm_status():
        from llm.client import health_check
        ok, msg = health_check()
        return {"llm_ok": ok, "llm_msg": msg}

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.errorhandler(403)
    def _forbidden(e):
        return render_template("error.html", code=403, message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def _not_found(e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(413)
    def _too_large(e):
        return render_template("error.html", code=413,
                               message=f"Upload too large. Limit is {settings.max_upload_mb} MB per document "
                                       f"({settings.max_audio_mb} MB for audio)."), 413

    @app.errorhandler(500)
    def _server_error(e):
        log.exception("Unhandled server error")
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500

    return app
