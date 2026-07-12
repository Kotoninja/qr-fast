"""
Ядро сервиса: генерация кастомизированного QR-кода в стиле Telegram.

Поддерживает:
- форму модулей (квадраты, скруглённые, круги, "точки")
- форму "глаз" (угловых квадратов-маркеров) — отдельно от обычных модулей
- заливку сплошным цветом или градиентом (линейный / радиальный)
- вставку логотипа/аватара в центр с белой подложкой (как в Telegram)
- фон: сплошной цвет или прозрачный (для наложения на цветной блок в UI)
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional, Tuple

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    SquareModuleDrawer,
    RoundedModuleDrawer,
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    VerticalBarsDrawer,
    HorizontalBarsDrawer,
)
from qrcode.image.styles.colormasks import (
    SolidFillColorMask,
    RadialGradiantColorMask,
    SquareGradiantColorMask,
    HorizontalGradiantColorMask,
    VerticalGradiantColorMask,
)
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_Q, ERROR_CORRECT_M, ERROR_CORRECT_L
from PIL import Image, ImageDraw

MODULE_DRAWERS = {
    "square": SquareModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "circle": CircleModuleDrawer,
    "gapped": GappedSquareModuleDrawer,
    "vertical_bars": VerticalBarsDrawer,
    "horizontal_bars": HorizontalBarsDrawer,
}

GRADIENTS = {
    "radial": RadialGradiantColorMask,
    "square": SquareGradiantColorMask,
    "horizontal": HorizontalGradiantColorMask,
    "vertical": VerticalGradiantColorMask,
}

ERROR_LEVELS = {
    "L": ERROR_CORRECT_L,   # ~7% восстановление
    "M": ERROR_CORRECT_M,   # ~15%
    "Q": ERROR_CORRECT_Q,   # ~25%
    "H": ERROR_CORRECT_H,   # ~30% — нужен, если в центр кладём логотип
}


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


@dataclass
class QRStyle:
    data: str                              # что кодируем (текст, ссылка и т.п.)
    module_style: str = "rounded"          # square | rounded | circle | gapped | vertical_bars | horizontal_bars
    fg_color: str = "#000000"              # основной цвет (или начало градиента)
    fg_color2: Optional[str] = None        # второй цвет градиента (если None — сплошная заливка)
    gradient: str = "radial"               # radial | square | horizontal | vertical
    bg_color: Optional[str] = "#FFFFFF"    # None -> прозрачный фон
    box_size: int = 10                     # размер одного модуля в пикселях
    border: int = 4                        # отступ в модулях (минимум 4 по спецификации)
    error_correction: str = "H"            # уровень коррекции ошибок
    logo_bytes: Optional[bytes] = None     # PNG/JPEG логотипа для центра
    logo_size_ratio: float = 0.22          # доля от общей ширины QR
    logo_padding: bool = True              # белая подложка-паддинг под логотипом
    rounded_logo: bool = True              # скруглять/делать круглым логотип


def generate_qr(style: QRStyle) -> Image.Image:
    if not style.data:
        raise ValueError("Поле data (содержимое QR-кода) не может быть пустым")

    qr = qrcode.QRCode(
        error_correction=ERROR_LEVELS.get(style.error_correction.upper(), ERROR_CORRECT_H),
        box_size=style.box_size,
        border=style.border,
    )
    qr.add_data(style.data)
    qr.make(fit=True)

    drawer_cls = MODULE_DRAWERS.get(style.module_style, RoundedModuleDrawer)
    module_drawer = drawer_cls()

    fg = _hex_to_rgb(style.fg_color)
    bg = _hex_to_rgb(style.bg_color) if style.bg_color else (255, 255, 255)

    if style.fg_color2:
        fg2 = _hex_to_rgb(style.fg_color2)
        mask_cls = GRADIENTS.get(style.gradient, RadialGradiantColorMask)
        color_mask = mask_cls(
            back_color=bg,
            center_color=fg,
            edge_color=fg2,
        ) if style.gradient == "radial" else mask_cls(
            back_color=bg,
            left_color=fg,
            right_color=fg2,
        ) if style.gradient in ("horizontal", "square") else mask_cls(
            back_color=bg,
            top_color=fg,
            bottom_color=fg2,
        )
    else:
        color_mask = SolidFillColorMask(back_color=bg, front_color=fg)

    embedded_image = None
    if style.logo_bytes:
        embedded_image = _prepare_logo(style.logo_bytes, style.rounded_logo)

    kwargs = {}
    if embedded_image is not None:
        kwargs["embeded_image"] = embedded_image  # опечатка в самой библиотеке, имя параметра именно такое
        kwargs["embeded_image_ratio"] = style.logo_size_ratio

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=module_drawer,
        color_mask=color_mask,
        **kwargs,
    )
    img = img.convert("RGBA")

    # Если фон должен быть прозрачным — заменяем bg-цвет на альфа-канал
    if style.bg_color is None:
        img = _make_background_transparent(img, bg)

    return img


def _prepare_logo(logo_bytes: bytes, rounded: bool) -> Image.Image:
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

    # Приводим к квадрату (обрезаем по центру)
    w, h = logo.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    logo = logo.crop((left, top, left + side, top + side))

    size = 300
    logo = logo.resize((size, size), Image.LANCZOS)

    if rounded:
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        logo.putalpha(mask)

    # Белая подложка чуть больше самого лого — как у Telegram
    pad = int(size * 0.14)
    canvas_size = size + pad * 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 255))
    if rounded:
        cmask = Image.new("L", (canvas_size, canvas_size), 0)
        ImageDraw.Draw(cmask).ellipse((0, 0, canvas_size, canvas_size), fill=255)
        canvas.putalpha(cmask)
    canvas.paste(logo, (pad, pad), logo)
    return canvas


def _make_background_transparent(img: Image.Image, bg_rgb: Tuple[int, int, int]) -> Image.Image:
    data = img.getdata()
    new_data = []
    for pixel in data:
        r, g, b = pixel[0], pixel[1], pixel[2]
        if (r, g, b) == bg_rgb:
            new_data.append((r, g, b, 0))
        else:
            new_data.append(pixel)
    img.putdata(new_data)
    return img


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
