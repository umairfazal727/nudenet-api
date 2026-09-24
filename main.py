from pathlib import Path
import os
import shutil
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from nudenet import NudeDetector

MODEL_PATH = Path(__file__).resolve().parent / "models" / "320n.onnx"
MIN_MODEL_BYTES = 1_000_000

# Exposed regions that should mark an upload as NSFW for a moderation check.
EXPLICIT_LABELS = {
    "FEMALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}


def load_detector() -> NudeDetector:
    if not MODEL_PATH.is_file() or MODEL_PATH.stat().st_size < MIN_MODEL_BYTES:
        raise RuntimeError(
            f"ONNX model missing or invalid at {MODEL_PATH}. "
            "Commit models/320n.onnx with the app. NudeNet must not download a checkpoint at startup."
        )
    return NudeDetector(model_path=str(MODEL_PATH), inference_resolution=320)


app = FastAPI()
detector = load_detector()


@app.get("/")
def health():
    return {"status": "ok", "model": MODEL_PATH.name}


@app.post("/detect")
async def detect_nudity(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    filename = file.filename or "upload.jpg"
    suffix = os.path.splitext(filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        detections = detector.detect(tmp_path)
        return {
            "nsfw": any(item.get("class") in EXPLICIT_LABELS for item in detections),
            "detections": detections,
        }
    finally:
        os.remove(tmp_path)
