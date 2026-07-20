"""
HTTP-сервис для кастомизации QR-кодов.

Запуск:
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8000

Открыть в браузере:
    http://localhost:8000            -> демо-страница с live-настройкой
    http://localhost:8000/docs       -> Swagger UI (можно дергать API руками)
"""

import base64
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from qr_core import QRStyle, generate_qr, image_to_png_bytes

app = FastAPI(title="QR fast", redoc_url=None, docs_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    with open("./index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api", include_in_schema=False)
def overridden_swagger():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="QR-Fast API",
        swagger_favicon_url="static/images/favicon.svg",
    )


async def _build_image(
    data: str,
    module_style: str,
    fg_color: str,
    fg_color2: Optional[str],
    gradient: str,
    bg_color: Optional[str],
    box_size: int,
    border: int,
    error_correction: str,
    logo_size_ratio: float,
    rounded_logo: bool,
    logo: Optional[UploadFile],
):
    logo_bytes = await logo.read() if logo is not None and logo.filename else None

    style = QRStyle(
        data=data,
        module_style=module_style,
        fg_color=fg_color,
        fg_color2=fg_color2 or None,
        gradient=gradient,
        bg_color=(bg_color or None) if bg_color != "transparent" else None,
        box_size=box_size,
        border=border,
        error_correction=error_correction,
        logo_bytes=logo_bytes,
        logo_size_ratio=logo_size_ratio,
        rounded_logo=rounded_logo,
    )
    try:
        return generate_qr(style)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate")
async def generate_png(
    data: str = Form(...),
    module_style: str = Form("rounded"),
    fg_color: str = Form("#000000"),
    fg_color2: Optional[str] = Form(None),
    gradient: Literal["radial", "horizontal", "vertical"] = Form("radial"),
    bg_color: Optional[str] = Form("#FFFFFF"),
    box_size: int = Form(10),
    border: int = Form(4),
    error_correction: str = Form("H"),
    logo_size_ratio: float = Form(0.22),
    rounded_logo: bool = Form(True),
    logo: Optional[UploadFile] = File(None),
):
    """
    Возвращает готовый PNG-файл кастомизированного QR-кода.\n
    Чем крупнее логотип и выше плотность данных (длинная ссылка), тем выше риск, что код перестанет сканироваться. Используйте error_correction=H при вставке логотипа и <b>не</b> делайте logo_size_ratio больше ~0.25.
    """
    img = await _build_image(
        data,
        module_style,
        fg_color,
        fg_color2,
        gradient,
        bg_color,
        box_size,
        border,
        error_correction,
        logo_size_ratio,
        rounded_logo,
        logo,
    )
    return Response(content=image_to_png_bytes(img), media_type="image/png")


@app.post("/generate-base64")
async def generate_base64(
    data: str = Form(...),
    module_style: str = Form("rounded"),
    fg_color: str = Form("#000000"),
    fg_color2: Optional[str] = Form(None),
    gradient: Literal["radial", "horizontal", "vertical"] = Form("radial"),
    bg_color: Optional[str] = Form("#FFFFFF"),
    box_size: int = Form(10),
    border: int = Form(4),
    error_correction: Literal["L", "M", "Q", "H"] = Form("H"),
    logo_size_ratio: float = Form(0.22),
    rounded_logo: bool = Form(True),
    logo: Optional[UploadFile] = File(None),
):
    """
    То же самое, но в виде JSON с картинкой в base64 — удобно дергать из фронта через fetch().\n
    Чем крупнее логотип и выше плотность данных (длинная ссылка), тем выше риск, что код перестанет сканироваться. Используйте error_correction=H при вставке логотипа и <b>не</b> делайте logo_size_ratio больше ~0.25.
    """
    img = await _build_image(
        data,
        module_style,
        fg_color,
        fg_color2,
        gradient,
        bg_color,
        box_size,
        border,
        error_correction,
        logo_size_ratio,
        rounded_logo,
        logo,
    )
    png_bytes = image_to_png_bytes(img)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return JSONResponse({"image": f"data:image/png;base64,{b64}"})
