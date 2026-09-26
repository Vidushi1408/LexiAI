# tests/test_classifier.py
"""Exercises the real (non-mocked) /clustering tagging classifier end to end — skipped where
torch isn't installed, e.g. CI's lightweight "Lint, test, eval gate" job (see the comment atop
requirements-ci.txt). That job instead tests webapp/blueprints/features.py's /clustering route
against a fully mocked models.classifier (see tests/test_webapp.py)."""
import pytest

pytest.importorskip("torch")

import models.classifier as classifier
from models.training_data import LABEL_MAP


def test_available_when_a_trained_model_is_committed():
    assert classifier.available() is True


def test_labels_match_the_training_data():
    assert set(classifier.get_labels()) == set(LABEL_MAP)


def test_classify_sentences_returns_one_prediction_per_sentence_with_a_known_label():
    sentences = ["Payment is due within thirty days of invoice.",
                 "The vendor shall indemnify the client against third-party claims."]
    predictions = classifier.classify_sentences(sentences)
    assert len(predictions) == len(sentences)
    for label, confidence in predictions:
        assert label in LABEL_MAP
        assert 0.0 <= confidence <= 1.0


def test_classify_sentences_handles_empty_input():
    assert classifier.classify_sentences([]) == []
