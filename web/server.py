"""
وب‌سرور FastAPI: مسیر دانلود مستقیم فایل‌ها + پنل مدیریت ساده.
با uvicorn، همزمان با بات (توی همون event loop) اجرا می‌شه — به bot.py نگاه کن.
"""
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from config import LINK_TTL_HOURS, PUBLIC_BASE_URL
from utils.helpers import format_size
from web import store
from web.settings import get_settings, update_settings
from web.auth import require_admin

app = FastAPI(title="TeleTube", docs_url=None, redoc_url=None)


@app.get("/")
async def root():
    return {"service": "TeleTube", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/files/{token}")
async def download_file(token: str):
    entry = store.get_link(token)
    if not entry:
        raise HTTPException(status_code=404, detail="لینک پیدا نشد یا منقضی شده")

    import os
    if not os.path.exists(entry["file_path"]):
        raise HTTPException(status_code=404, detail="فایل دیگه روی سرور موجود نیست")

    store.record_download(token)
    filename = f"{entry['title']}.mp4"
    return FileResponse(
        entry["file_path"],
        media_type="video/mp4",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# پنل مدیریت
# ---------------------------------------------------------------------------

def _fmt_time(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _render_admin_page(settings: dict, links: list, base_url: str) -> str:
    checked_direct = "checked" if settings.get("enable_direct_links", True) else ""
    checked_channel = "checked" if settings.get("enable_channel_delivery", True) else ""
    checked_nimbaha = "checked" if settings.get("enable_nimbaha", False) else ""

    rows = ""
    for entry in links:
        link_url = f"{base_url}/files/{entry['token']}" if base_url else f"/files/{entry['token']}"
        rows += f"""
        <tr>
          <td>{entry['title']}</td>
          <td>{format_size(entry['size_bytes']) or '-'}</td>
          <td>{_fmt_time(entry['created_at'])}</td>
          <td>{_fmt_time(entry['expires_at'])}</td>
          <td>{entry['downloads']}</td>
          <td><a href="{link_url}" target="_blank">لینک</a></td>
          <td>
            <form method="post" action="/admin/links/{entry['token']}/delete" style="margin:0">
              <button type="submit" class="danger">حذف</button>
            </form>
          </td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="7" style="text-align:center;color:#888">هیچ لینک فعالی نیست</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>پنل مدیریت TeleTube</title>
<style>
  body {{ font-family: Tahoma, sans-serif; background:#0f1115; color:#e6e6e6; margin:0; padding:24px; }}
  h1 {{ font-size: 20px; }}
  .card {{ background:#1a1d24; border-radius:10px; padding:16px 20px; margin-bottom:20px; }}
  label {{ display:flex; align-items:center; gap:8px; margin:8px 0; }}
  table {{ width:100%; border-collapse: collapse; font-size:14px; }}
  th, td {{ text-align:right; padding:8px 6px; border-bottom:1px solid #2a2e37; }}
  a {{ color:#4ea1ff; }}
  button {{ background:#2a2e37; color:#e6e6e6; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; }}
  button.primary {{ background:#2f6feb; }}
  button.danger {{ background:#7a2626; }}
  button:hover {{ opacity:0.85; }}
</style>
</head>
<body>
  <h1>پنل مدیریت TeleTube</h1>

  <div class="card">
    <h2>تنظیمات</h2>
    <form method="post" action="/admin/settings">
      <label><input type="checkbox" name="enable_direct_links" {checked_direct}> فعال بودن لینک مستقیم دانلود</label>
      <label><input type="checkbox" name="enable_channel_delivery" {checked_channel}> فعال بودن ارسال از طریق کانال تلگرام</label>
      <label><input type="checkbox" name="enable_nimbaha" {checked_nimbaha}> ارائه‌ی لینک نیم‌بها (ترافیک داخلی)</label>
      <p style="color:#888;font-size:13px">اگه هر دو غیرفعال بشن، ارسال از طریق کانال به‌صورت خودکار فعال می‌مونه.</p>
      <button type="submit" class="primary">ذخیره تنظیمات</button>
    </form>
  </div>

  <div class="card">
    <h2>لینک‌های فعال (اعتبار پیش‌فرض: {LINK_TTL_HOURS} ساعت)</h2>
    <table>
      <tr><th>عنوان</th><th>حجم</th><th>ساخته‌شده</th><th>انقضا</th><th>تعداد دانلود</th><th>لینک</th><th></th></tr>
      {rows}
    </table>
  </div>
</body>
</html>"""


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(_user: str = Depends(require_admin)):
    settings = get_settings()
    links = store.list_links()
    return _render_admin_page(settings, links, PUBLIC_BASE_URL)


@app.post("/admin/settings")
async def admin_update_settings(
    enable_direct_links: bool = Form(False),
    enable_channel_delivery: bool = Form(False),
    enable_nimbaha: bool = Form(False),
    _user: str = Depends(require_admin),
):
    if not enable_direct_links and not enable_channel_delivery:
        enable_channel_delivery = True

    update_settings({
        "enable_direct_links": enable_direct_links,
        "enable_channel_delivery": enable_channel_delivery,
        "enable_nimbaha": enable_nimbaha,
    })
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/links/{token}/delete")
async def admin_delete_link(token: str, _user: str = Depends(require_admin)):
    store.delete_link(token, delete_file=True)
    return RedirectResponse(url="/admin", status_code=303)
