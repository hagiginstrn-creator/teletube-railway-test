"""توابع کمکی عمومی که در چند جای پروژه استفاده می‌شن."""
import re
import base64
from urllib.parse import quote
import requests

def extract_video_id(url):
    """شناسه ویدیوی یوتیوب رو از فرمت‌های مختلف لینک استخراج می‌کنه."""
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    return None


def sanitize_filename(name):
    """کاراکترهای غیرمجاز برای نام فایل رو با _ جایگزین می‌کنه."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def progress_bar(percent, width=12):
    """یک نوار پیشرفت متنی می‌سازه، مثلا: ####--------"""
    percent = max(0, min(100, percent))
    filled = int(width * percent / 100)
    return "#" * filled + "-" * (width - filled)


def format_size(num_bytes):
    """بایت رو به یک رشته‌ی خوانا مثل «85.3 MB» تبدیل می‌کنه. اگه None باشه
    (یعنی حجم فرمت نامعلوم بود)، None برمی‌گردونه."""
    if not num_bytes:
        return None
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def make_nimbaha_link(direct_url, filename):
    """لینک نیم‌بهای آروان‌کلود رو از روی لینک مستقیم می‌سازه."""
    encoded = base64.b64encode(direct_url.encode("utf-8")).decode("ascii")
    safe_name = quote(filename)
    safe_encoded = quote(encoded, safe="")
    return f"https://nimbaha.ehsanpakar90.arvanedge.ir/file/{safe_name}?url={safe_encoded}"



import re

def make_urldl_link(direct_url, timeout=15):
    """
    لینک نیم‌بهای urldl.ir رو می‌سازه. چون این سایت شناسه/توکن رو سمت
    سرور خودش تولید می‌کنه (برخلاف nimbaha)، باید واقعاً باهاش تماس بگیریم.
    خروجی: لینک نهایی یا None اگه fail بشه.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    try:
        resp1 = session.post(
            "https://urldl.ir/add-link",
            data={"fileurl": direct_url},
            timeout=timeout,
            allow_redirects=False,
        )
        location = resp1.headers.get("Location")
        if not location:
            return None

        download_page_url = f"https://urldl.ir/{location.lstrip('/')}"
        resp2 = session.get(download_page_url, timeout=timeout)
        match = re.search(r"/dl/[^\"'<> ]+", resp2.text)
        if not match:
            return None

        return f"https://urldl.ir{match.group(0)}"
    except Exception:
        return None
