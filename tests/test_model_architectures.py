# tests/test_model_architectures.py
"""num_classes must actually reach the underlying nn.Module for all three architectures — before
this, train_ann/train_cnn/train_lstm silently hardcoded 4 classes regardless of what was passed,
which would have quietly mismatched the 7-tag contract-sentence dataset (models/training_data.py).
Skipped where torch isn't installed (see tests/test_classifier.py for why)."""
import numpy as np
import pytest

pytest.importorskip("torch")

from models.ann_model import train_ann
from models.cnn_model import train_cnn
from models.lstm_model import train_lstm


def _tiny_dataset(num_classes: int, per_class: int = 4, dim: int = 384):
    rng = np.random.default_rng(0)
    X, y = [], []
    for c in range(num_classes):
        X.append(rng.normal(loc=c, scale=0.1, size=(per_class, dim)).astype(np.float32))
        y += [c] * per_class
    return np.concatenate(X), np.array(y)


@pytest.mark.parametrize("train_fn", [train_ann, train_cnn, train_lstm])
def test_num_classes_propagates_to_the_model_output_layer(train_fn):
    num_classes = 7
    X, y = _tiny_dataset(num_classes)
    model, _, _ = train_fn(X, y, X, y, epochs=1, num_classes=num_classes)

    import torch
    with torch.no_grad():
        logits = model(torch.FloatTensor(X[:1]))
    assert logits.shape[-1] == num_classes
