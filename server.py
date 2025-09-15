import os, requests, hmac, hashlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from seo import build_seo_html
from translator import translate_text

WP_URL = os.environ["WP_URL"].rstrip("/")
WP_USER = os.environ["WP_USER"]
WP_APP_PASS = os.environ["WP_APP_PASS"]
SHARED_SECRET = os.environ.get("SHARED_SECRET", "")

app = FastAPI()

def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not SHARED_SECRET:
        return True
    mac = hmac.new(SHARED_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature or "")

def wp_update_post(post_id: int, content_html: str, translated: bool, publish: bool):
    data = {"content": content_html}
    if publish:
        data["status"] = "publish"
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, WP_APP_PASS),
        json=data, timeout=60
    )
    if not r.ok:
        raise HTTPException(status_code=502, detail=f"WP update failed: {r.status_code} {r.text}")
    # متاهای ضد لوپ:
    try:
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            auth=(WP_USER, WP_APP_PASS),
            json={"meta": {"_ss_translated": 1, "_ss_translating": 0}},
            timeout=30
        )
    except Exception:
        pass
    return r.json()

@app.post("/translate")
async def translate_post(req: Request):
    raw = await req.body()
    sig = req.headers.get("X-WP-Signature")
    if not verify_signature(raw, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await req.json()
    post_id = int(data["post_id"])
    title   = data.get("title") or ""
    content = data.get("content") or ""
    was_draft = bool(data.get("was_draft", False))

    fa = translate_text(content)
    html = fa if "<html" in fa.lower() else build_seo_html(fa, title_hint=title)

    # اگر از Draft شروع کرده بودی، ما Publish می‌کنیم؛ اگر مستقیم Publish بود، همان را آپدیت می‌کنیم
    res = wp_update_post(post_id, html, translated=True, publish=was_draft)
    return JSONResponse({"ok": True, "id": res.get("id"), "link": res.get("link")})
