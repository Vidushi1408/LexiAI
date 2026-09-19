# models/train_all.py
# Run: python -m models.train_all
"""Trains ANN, CNN, LSTM with the expanded dataset and compares them."""
# pyrefly: ignore [missing-import]
import os, sys, torch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_prep  import prepare_dataset
from models.ann_model  import ANNClassifier, train_ann
from models.cnn_model  import CNNClassifier, train_cnn
from models.lstm_model import LSTMClassifier, train_lstm
from models.evaluator  import evaluate_model, compare_models


def main():
    print("\n🚀 Lexi AI — Model Training\n")
    X_tr, X_v, X_te, y_tr, y_v, y_te = prepare_dataset()

    print("\n── Training ANN ──")
    ann, _, _ = train_ann(X_tr, y_tr, X_v, y_v, epochs=80, lr=0.0008)

    print("\n── Training CNN ──")
    cnn, _, _ = train_cnn(X_tr, y_tr, X_v, y_v, epochs=80, lr=0.0008)

    print("\n── Training LSTM ──")
    lstm, _, _ = train_lstm(X_tr, y_tr, X_v, y_v, epochs=80, lr=0.0008)

    print("\n📊 Evaluation on test set:")
    r_ann  = evaluate_model(ann,  X_te, y_te, "ANN")
    r_cnn  = evaluate_model(cnn,  X_te, y_te, "CNN")
    r_lstm = evaluate_model(lstm, X_te, y_te, "LSTM")
    compare_models({"ANN":r_ann,"CNN":r_cnn,"LSTM":r_lstm})

    os.makedirs("models/saved", exist_ok=True)
    torch.save(ann.state_dict(),  "models/saved/ann_model.pt")
    torch.save(cnn.state_dict(),  "models/saved/cnn_model.pt")
    torch.save(lstm.state_dict(), "models/saved/lstm_model.pt")
    print("\n✅ All models saved to models/saved/")

if __name__ == "__main__":
    main()