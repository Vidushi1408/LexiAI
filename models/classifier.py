# models/classifier.py
"""
Inference for the /clustering (Tagging) page — loads whichever of ANN/CNN/LSTM
models/train_all.py found to score best (models/saved/best_model.json) and classifies contract
sentences into the tags that page has always offered (Risk, Decision, Action Item, Deadline,
Financial, Compliance, Obligation; see models/training_data.py).

If no trained model has been committed or generated yet (`python -m models.train_all`),
`available()` returns False and callers fall back to a cruder heuristic — see
webapp/blueprints/features.py's clustering() route.
"""
import json
import os

# torch is NOT imported at module level: this module is imported (and its functions patched in
# tests) even where torch isn't installed — CI's main test job deliberately excludes it, since
# nothing used to depend on it (see requirements-ci.txt). Only classify_sentences() below, and
# the model-loading it triggers, actually needs it.

_SAVED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved")
_META_FILE = os.path.join(_SAVED_DIR, "best_model.json")

_model = None
_labels: list[str] | None = None
_load_attempted = False


def _load_best() -> None:
    global _model, _labels, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True

    if not os.path.exists(_META_FILE):
        return
    with open(_META_FILE) as f:
        meta = json.load(f)

    arch, num_classes, labels = meta["architecture"], meta["num_classes"], meta["labels"]
    weights_path = os.path.join(_SAVED_DIR, f"{arch}_model.pt")
    if not os.path.exists(weights_path):
        return

    if arch == "ann":
        from models.ann_model import load_model
    elif arch == "cnn":
        from models.cnn_model import load_model
    elif arch == "lstm":
        from models.lstm_model import load_model
    else:
        return

    _model = load_model(weights_path, num_classes=num_classes)
    _labels = labels


def available() -> bool:
    _load_best()
    return _model is not None


def get_labels() -> list[str]:
    """The tags the loaded model predicts, in class-index order. Empty if none is loaded."""
    _load_best()
    return _labels or []


def classify_sentences(sentences: list[str]) -> list[tuple[str, float]]:
    """Returns (label, confidence) for each sentence, in the same order. Callers should check
    `available()` first — this returns [] rather than raising when no model is loaded."""
    _load_best()
    if _model is None or not sentences:
        return []

    import torch
    from embeddings.sentence_embeddings import embed_sentences
    # use_cache=False: these are arbitrary uploaded-document sentences, not the fixed training
    # set — caching them to disk indefinitely would be an unbounded, unwanted retention path.
    vecs = embed_sentences(sentences, use_cache=False)

    with torch.no_grad():
        logits = _model(torch.FloatTensor(vecs))
        probs = torch.softmax(logits, dim=1)
        confidences, indices = probs.max(dim=1)

    assert _labels is not None
    return [(_labels[i], float(c)) for i, c in zip(indices.tolist(), confidences.tolist())]
