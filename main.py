from fastapi import FastAPI, UploadFile, File, HTTPException
from nudenet import NudeDetector
import shutil
import tempfile
import os

app = FastAPI()
detector = NudeDetector()

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/detect")
async def detect_nudity(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = detector.detect(tmp_path)
        return {"detections": result}
    finally:
        os.remove(tmp_path)