"""احراز هویت ساده (HTTP Basic Auth) برای پنل مدیریت."""
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import ADMIN_PANEL_USERNAME, ADMIN_PANEL_PASSWORD

security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if not ADMIN_PANEL_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="پنل مدیریت غیرفعاله چون ADMIN_PANEL_PASSWORD ست نشده.",
        )
    correct_username = secrets.compare_digest(credentials.username, ADMIN_PANEL_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PANEL_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="یوزرنیم یا پسورد اشتباهه",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
