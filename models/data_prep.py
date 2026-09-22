# models/data_prep.py
"""Training Data Preparation — uses expanded dataset"""
import numpy as np, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sklearn.model_selection import train_test_split
from embeddings.sentence_embeddings import embed_sentences
from models.training_data import TRAINING_DATA, LABEL_MAP


def prepare_dataset() -> tuple:
    print(f"[DATA] {len(TRAINING_DATA)} samples loaded")
    sentences, label_names = zip(*TRAINING_DATA)
    labels = np.array([LABEL_MAP[l] for l in label_names])
    dist   = {k: list(labels).count(v) for k,v in LABEL_MAP.items()}
    print(f"[DATA] Distribution: {dist}")
    print("[DATA] Generating embeddings (this takes ~1 min)...")
    X = embed_sentences(list(sentences))
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, labels, test_size=0.22, random_state=42, stratify=labels)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)
    print(f"[DATA] Train:{len(X_train)} Val:{len(X_val)} Test:{len(X_test)}")
    return X_train, X_val, X_test, y_train, y_val, y_test