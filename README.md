# Image Check API

A small HTTP API that checks **one uploaded image** and tells you whether it contains explicit content. It is meant for a backend such as Laravel: your app sends the image file, and this service returns a yes/no flag plus the regions it found.

There is no API key and no login. The service does not accept an image URL. It only accepts the image file itself.

The detector is [NudeNet](https://github.com/notAI-tech/NudeNet) `3.4.2` with the bundled `320n` model. The model file is stored in this repo at `models/320n.onnx`, so the server does not download a checkpoint when it starts.

## What you get back

`nsfw` is `true` only when the image contains at least one of these exposed regions:

- `FEMALE_GENITALIA_EXPOSED`
- `FEMALE_BREAST_EXPOSED`
- `MALE_GENITALIA_EXPOSED`
- `BUTTOCKS_EXPOSED`
- `ANUS_EXPOSED`

Faces, feet, belly, armpits, and covered regions can still appear in `detections` while `nsfw` stays `false`. Use `nsfw` for a simple allow/block decision. Use `detections` when you need the reason.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health check. Confirms the process is up and which model file is loaded. |
| `POST` | `/detect` | Check one image. |

### Health check

```http
GET /
```

```json
{
  "status": "ok",
  "model": "320n.onnx"
}
```

### Detect

```http
POST /detect
Content-Type: multipart/form-data
```

| Item | Required value |
| --- | --- |
| Form field name | `file` |
| Images per request | 1 |
| Auth header | none |
| Body | the image bytes, not a link |

Send a normal photo file. The file content type must start with `image/`.

| Works | Content type |
| --- | --- |
| `.jpg`, `.jpeg` | `image/jpeg` |
| `.png` | `image/png` |
| `.webp` | `image/webp` |
| `.bmp` | `image/bmp` |

Do not send a PDF, a text file, or JSON like `{"url": "https://example.com/photo.jpg"}`. A URL string is not an image, and this API will not fetch one.

Keep each image under about **5 MB**. The code has no hard size cap, but the model loads the whole file into memory and a very large photo can crash a small host. Phone-sized photos are enough. The model resizes the picture internally to 320×320.

Call **one image at a time** on a small Render instance (512 MB RAM).

A wrong file type returns `400`:

```json
{
  "detail": "File must be an image"
}
```

## Response JSON

A clean image:

```json
{
  "nsfw": false,
  "detections": []
}
```

An image with a match:

```json
{
  "nsfw": true,
  "detections": [
    {
      "class": "FEMALE_BREAST_EXPOSED",
      "score": 0.87,
      "box": [120, 40, 80, 90]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `nsfw` | `true` or `false`. `true` only for the five exposed classes listed above. |
| `detections` | Every region the model kept. Can be an empty list. |
| `class` | Region name. See the full list below. |
| `score` | Confidence from 0 to 1. Higher is more confident. Scores under about 0.25 are dropped before the response. |
| `box` | `[x, y, width, height]` in pixels of the original image. `x` and `y` are the top-left corner. |

Other class names the model can return:

`FEMALE_GENITALIA_COVERED`, `FACE_FEMALE`, `BUTTOCKS_EXPOSED`, `FEMALE_BREAST_EXPOSED`, `FEMALE_GENITALIA_EXPOSED`, `MALE_BREAST_EXPOSED`, `ANUS_EXPOSED`, `FEET_EXPOSED`, `BELLY_COVERED`, `FEET_COVERED`, `ARMPITS_COVERED`, `ARMPITS_EXPOSED`, `FACE_MALE`, `BELLY_EXPOSED`, `MALE_GENITALIA_EXPOSED`, `ANUS_COVERED`, `FEMALE_BREAST_COVERED`, `BUTTOCKS_COVERED`

## Call it from Laravel

Point this at your deployed host. Replace the example host with your real URL.

```php
$response = Http::timeout(120)
    ->attach(
        'file',
        file_get_contents($path),
        'photo.jpg',
        ['Content-Type' => 'image/jpeg']
    )
    ->post('https://YOUR-SERVICE.onrender.com/detect');

if ($response->successful()) {
    $nsfw = $response->json('nsfw');
    $detections = $response->json('detections');
}
```

`$path` must be a local file, such as `$request->file('photo')->getRealPath()`. Do not pass a remote URL string as the file contents.

`timeout(120)` matters on Render's free instance. After 15 minutes with no traffic the service sleeps, and the next call can take about a minute to wake up.

The same request with curl:

```bash
curl -F "file=@photo.jpg;type=image/jpeg" https://YOUR-SERVICE.onrender.com/detect
```

## How often you can call it

This app does not issue tokens and does not count requests. You can call it as long as the host stays up.

If you deploy on Render's free instance, the limits come from Render, not from this code:

- 512 MB RAM and 0.1 CPU
- sleeps after 15 minutes without traffic
- about 750 free instance hours per workspace each month
- a Hobby workspace includes a monthly outbound bandwidth allowance, then Render bills extra traffic

A paid always-on instance does not sleep. The `$1` charge on a Render account is billing. It does not add an API key or a request pack.

## Run it on your machine

Python 3.10 or newer.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/`. You should see `{"status":"ok","model":"320n.onnx"}`.

`models/320n.onnx` must be present and larger than 1 MB. If that file is missing, the process stops at startup instead of downloading a model.

## Deploy on Render

Create a Web Service from this repo.

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/` |

`render.yaml` uses the service name `image-check-api` and the Singapore region. Those values apply when you deploy with a Render Blueprint. Changing the file does not move a service you already created in the dashboard.

Name the public service so the hostname does not contain the word `nude`. Some networks reset the TLS connection when that word is in the URL, which looks like cURL error 35 (`Connection was reset`) before the image is sent. `image-check-api` avoids that. The API behavior is the same regardless of the hostname.

After deploy, open `https://YOUR-SERVICE.onrender.com/` and confirm the health JSON before pointing Laravel at `/detect`.
