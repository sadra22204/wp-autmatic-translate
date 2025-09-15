import os, base64, time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

STATE_JSON_PATH = "state.json"

def ensure_state_file_from_env():
    b64 = os.environ.get("STATE_JSON_B64")
    if not b64:
        return
    with open(STATE_JSON_PATH, "wb") as f:
        f.write(base64.b64decode(b64.encode("utf-8")))

def translate_text(content_html: str) -> str:
    ensure_state_file_from_env()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-gpu"])
        context = browser.new_context(storage_state=STATE_JSON_PATH if os.path.exists(STATE_JSON_PATH) else None, viewport={"width":1280,"height":900})
        page = context.new_page()

        # پیمایش و اطمینان از لاگین
        page.goto("https://gemini.google.com", wait_until="networkidle")
        time.sleep(1.5)

        # نکته: سلکتورها را با DevTools نهایی کن
        # 1) فوکوس روی باکس ورودی
        page.click("textarea[aria-label]", timeout=15000)
        # 2) دستور ترجمه با تاکید بر حفظ ساختار HTML
        prompt = f"Translate the following HTML to Persian. Keep HTML structure, preserve links, headings, lists. Return only valid HTML:\n\n{content_html}"
        page.fill("textarea[aria-label]", prompt)
        page.keyboard.press("Enter")

        # 3) انتظار تا پاسخ رندر شود؛ سپس متن را از DOM بخوان (کلید: از Clipboard استفاده نکن)
        # سلکتور پاسخ را با DevTools شناسایی کن؛ موقتاً main را می‌خوانیم:
        try:
            page.wait_for_selector("main", timeout=120000)
        except PWTimeout:
            browser.close()
            raise RuntimeError("Translation timeout")
        response_html = page.inner_html("main")

        browser.close()
        return response_html

