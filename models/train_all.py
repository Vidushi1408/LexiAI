# models/train_all.py
# Run: python -m models.train_all
"""Trains ANN, CNN, LSTM on the contract-sentence tagging dataset, compares them, and records
which one wins in models/saved/best_model.json — that file is what models/classifier.py (the
inference path used by /clustering) reads to know which architecture and label set to load."""
import json
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_prep import prepare_dataset
from models.ann_model import train_ann
from models.cnn_model import train_cnn
from models.evaluator import compare_models, evaluate_model
from models.lstm_model import train_lstm
from models.training_data import ID_TO_LABEL, LABEL_MAP


def main():
    print("\n🚀 Lexi AI — Model Training\n")
    num_classes = len(LABEL_MAP)
    X_tr, X_v, X_te, y_tr, y_v, y_te = prepare_dataset()

    print("\n── Training ANN ──")
    ann, _, _ = train_ann(X_tr, y_tr, X_v, y_v, epochs=80, lr=0.0008, num_classes=num_classes)

    print("\n── Training CNN ──")
    cnn, _, _ = train_cnn(X_tr, y_tr, X_v, y_v, epochs=80, lr=0.0008, num_classes=num_classes)

    print("\n── Training LSTM ──")
    lstm, _, _ = train_lstm(X_tr, y_tr, X_v, y_v, epochs=80, lr=0.0008, num_classes=num_classes)

    print("\n📊 Evaluation on test set:")
    results = {"ann": evaluate_model(ann, X_te, y_te, "ANN"),
               "cnn": evaluate_model(cnn, X_te, y_te, "CNN"),
               "lstm": evaluate_model(lstm, X_te, y_te, "LSTM")}
    compare_models({"ANN": results["ann"], "CNN": results["cnn"], "LSTM": results["lstm"]})

    os.makedirs("models/saved", exist_ok=True)
    torch.save(ann.state_dict(), "models/saved/ann_model.pt")
    torch.save(cnn.state_dict(), "models/saved/cnn_model.pt")
    torch.save(lstm.state_dict(), "models/saved/lstm_model.pt")

    best_arch = max(results, key=lambda a: results[a]["f1"])
    with open("models/saved/best_model.json", "w") as f:
        json.dump({"architecture": best_arch, "f1": results[best_arch]["f1"],
                   "num_classes": num_classes, "labels": [ID_TO_LABEL[i] for i in range(num_classes)]},
                  f, indent=2)
    print(f"\n✅ All models saved to models/saved/ — best: {best_arch.upper()} "
          f"(F1={results[best_arch]['f1']:.4f}), recorded in models/saved/best_model.json")


if __name__ == "__main__":
    main()