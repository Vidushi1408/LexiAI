# models/ann_model.py

"""
ANN — Artificial Neural Network Classifier
--------------------------------------------
Architecture:
  Input (384) → Dense(256) → ReLU → Dropout
              → Dense(128) → ReLU → Dropout
              → Dense(64)  → ReLU
              → Output(4)  → Softmax

Why this architecture?
- 384 input = sentence embedding size
- We gradually reduce dimensions (384→256→128→64→4)
  like funneling down to the answer
- ReLU adds non-linearity (lets model learn complex patterns)
- Dropout prevents overfitting (randomly turns off neurons during training)
- Softmax outputs 4 probabilities (one per class) that sum to 1.0
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


class ANNClassifier(nn.Module):
    """
    Feedforward Neural Network for sentence classification.
    Inherits from nn.Module (PyTorch base class for all models).
    """

    def __init__(self, input_dim: int = 384, num_classes: int = 4):
        """
        Defines the layers of the network.

        Args:
            input_dim (int): Size of input embeddings (384 for MiniLM)
            num_classes (int): Number of output classes (4)
        """
        super(ANNClassifier, self).__init__()

        # nn.Sequential chains layers — input flows through them in order
        self.network = nn.Sequential(

            # Layer 1: 384 → 256
            nn.Linear(input_dim, 256),  # Fully connected layer
            nn.ReLU(),                   # Activation: max(0, x)
            nn.Dropout(0.3),             # Randomly zero 30% of neurons

            # Layer 2: 256 → 128
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),

            # Layer 3: 128 → 64
            nn.Linear(128, 64),
            nn.ReLU(),

            # Output Layer: 64 → 4 (one score per class)
            nn.Linear(64, num_classes)
            # No softmax here — CrossEntropyLoss applies it internally
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass — how data flows through the network.

        Args:
            x: Input tensor of shape (batch_size, 384)

        Returns:
            Tensor of shape (batch_size, 4) — raw class scores (logits)
        """
        return self.network(x)


def train_ann(X_train, y_train, X_val, y_val,
              epochs: int = 50, lr: float = 0.001, num_classes: int = 4) -> tuple:
    """
    Trains the ANN model.

    Args:
        X_train, y_train: Training embeddings and labels
        X_val,   y_val  : Validation embeddings and labels
        epochs (int)    : Number of training iterations
        lr (float)      : Learning rate (how big each weight update is)
        num_classes (int): Number of output classes

    Returns:
        tuple: (trained_model, train_losses, val_losses)
    """

    # ── Convert numpy arrays to PyTorch tensors ──────────────────
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_val_t   = torch.FloatTensor(X_val)
    y_val_t   = torch.LongTensor(y_val)

    # ── DataLoader batches the data (processes 16 samples at a time) ──
    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader  = DataLoader(train_dataset, batch_size=16, shuffle=True)

    # ── Initialize model, loss function, optimizer ────────────────
    model     = ANNClassifier(num_classes=num_classes)
    criterion = nn.CrossEntropyLoss()       # Good for multi-class classification
    optimizer = optim.Adam(model.parameters(), lr=lr)  # Adam: adaptive learning rate

    train_losses, val_losses = [], []

    print(f"\n[ANN] Training for {epochs} epochs...")

    for epoch in range(epochs):

        # ── Training phase ────────────────────────────────────────
        model.train()  # Enable dropout (training mode)
        epoch_loss = 0

        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()              # Clear old gradients
            outputs = model(X_batch)           # Forward pass
            loss    = criterion(outputs, y_batch)  # Calculate loss
            loss.backward()                    # Backpropagation
            optimizer.step()                   # Update weights
            epoch_loss += loss.item()

        avg_train_loss = epoch_loss / len(train_loader)
        train_losses.append(avg_train_loss)

        # ── Validation phase ──────────────────────────────────────
        model.eval()   # Disable dropout (evaluation mode)
        with torch.no_grad():  # Don't calculate gradients (saves memory)
            val_outputs = model(X_val_t)
            val_loss    = criterion(val_outputs, y_val_t).item()
            val_losses.append(val_loss)

        # Print progress every 10 epochs
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch [{epoch+1}/{epochs}] "
                  f"Train Loss: {avg_train_loss:.4f} | "
                  f"Val Loss: {val_loss:.4f}")

    print("[ANN] Training complete! ✅")
    return model, train_losses, val_losses


def save_model(model, path: str = "models/saved/ann_model.pt"):
    """Saves trained model weights to disk."""
    import os
    os.makedirs("models/saved", exist_ok=True)
    torch.save(model.state_dict(), path)
    print(f"[ANN] Model saved to {path}")


def load_model(path: str = "models/saved/ann_model.pt", num_classes: int = 4) -> ANNClassifier:
    """Loads saved model weights from disk."""
    model = ANNClassifier(num_classes=num_classes)
    model.load_state_dict(torch.load(path))
    model.eval()
    print(f"[ANN] Model loaded from {path}")
    return model