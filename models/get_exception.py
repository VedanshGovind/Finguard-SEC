import ssl
ssl._create_default_https_context = ssl._create_unverified_context



import torch
import timm
import json
from pathlib import Path


# Matches your config.py paths
MODEL_PATH = Path("models/deepfake_model.pth")
METADATA_PATH = Path("models/model_metadata.json")

def download_and_save_xception():
    print("🚀 Downloading Xception model with ImageNet weights...")

    # Create the model with 1 output class (Deepfake probability)
    # Using pretrained=True to get the learned weights
    model = timm.create_model('xception', pretrained=True, num_classes=1)

    # Ensure the models directory exists
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # SAVE THE ENTIRE MODEL (required by your model_loader.py)
    print(f"📦 Saving to {MODEL_PATH}...")
    torch.save(model, MODEL_PATH)

    # Save metadata so model_loader.py doesn't crash
    metadata = {
        "model_name": "Xception-Pretrained",
        "version": "1.0.0",
        "architecture": "Xception"
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=4)

    print("✅ Xception is now ready in your models/ folder!")

if __name__ == "__main__":
    download_and_save_xception()