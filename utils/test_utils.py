# Run this from your project root: python utils/test_utils.py

from utils.pdf_reader import extract_text_from_txt
from utils.file_handler import save_processed_data, load_processed_data

# Test 1: Create a sample text file and read it
sample_text = """
Machine learning is a subset of artificial intelligence.
Neural networks are inspired by the human brain.
Deep learning uses multiple layers of neural networks.
"""

# Save it as a .txt file first
with open("data/raw/sample_notes.txt", "w") as f:
    f.write(sample_text)

# Read it back
text = extract_text_from_txt("data/raw/sample_notes.txt")
print("=== Extracted Text ===")
print(text)

# Test 2: Save some mock processed data
mock_data = {
    "clean_text": text,
    "word_count": len(text.split()),
    "tokens": text.split()[:10]  # first 10 words as mock tokens
}

save_processed_data(mock_data, "test_output.json")

# Test 3: Load it back
loaded = load_processed_data("test_output.json")
print("\n=== Loaded Processed Data ===")
print(f"Word count: {loaded['word_count']}")
print(f"First 10 tokens: {loaded['tokens']}")

print("\n✅ All utils tests passed!")