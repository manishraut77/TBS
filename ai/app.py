import io
import requests

import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://mrtbs.vercel.app/diagnosis",  # or your custom domain
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    imageUrl: str


# ---------- Device ----------
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")


# ---------- Transform (must match training) ----------
imagenet_mean = [0.485, 0.456, 0.406]
imagenet_std  = [0.229, 0.224, 0.225]

eval_transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
])


# ---------- Load checkpoint + model once ----------
try:
    ckpt = torch.load("models/resnet18_tb.pt", map_location=device)

    model = models.resnet18(weights=None)  # we load our own weights
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(ckpt["model_state"])
    model.to(device)
    model.eval()

    idx_to_class = {v: k for k, v in ckpt["class_to_idx"].items()}

except Exception as e:
    # If model fails to load, the API should still run but /predict will error.
    model = None
    idx_to_class = None
    load_error = str(e)


@app.get("/health")
def health():
    return {
        "ok": True,
        "device": str(device),
        "modelLoaded": model is not None,
    }


@app.post("/predict")
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=500, detail=f"Model not loaded: {load_error}")

    image_url = (req.imageUrl or "").strip()
    if not image_url:
        raise HTTPException(status_code=400, detail="Missing imageUrl")

    # 1) Download image
    try:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        image_bytes = resp.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch imageUrl: {e}")

    # 2) Load image with PIL
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    # 3) Preprocess
    x = eval_transform(img).unsqueeze(0).to(device)  # [1,3,224,224]

    # 4) Inference
    with torch.no_grad():
        logits = model(x)                 # [1,2]
        probs = torch.softmax(logits, 1)  # [1,2]
        conf, pred_idx = torch.max(probs, dim=1)

    pred_idx = int(pred_idx.item())
    label = idx_to_class[pred_idx]
    confidence = float(conf.item())

    return {
        "ok": True,
        "imageUrl": image_url,
        "label": label,
        "confidence": confidence,
        "probs": {
            idx_to_class[0]: float(probs[0, 0].item()),
            idx_to_class[1]: float(probs[0, 1].item()),
        },
    }

