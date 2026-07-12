# QR Studio — сервис кастомизации QR-кодов

Небольшой сервис на FastAPI: принимает данные (текст/ссылку) и параметры
стиля, отдаёт кастомизированный QR-код — как в Telegram (скруглённые модули,
градиенты, логотип по центру).

## Запуск

```bash
cd qr_service
python -m venv venv && source venv/bin/activate   # опционально
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Открыть в браузере: **http://localhost:8000** — там демо-страница с живой
настройкой (меняешь параметры слева — превью справа обновляется само).

Swagger (чтобы дёргать API вручную/из другого сервиса): **http://localhost:8000/docs**

## API

### `POST /generate`
Возвращает готовый PNG-файл.

### `POST /generate-base64`
Возвращает JSON `{ "image": "data:image/png;base64,..." }` — удобно для фронта.

**Параметры формы (multipart/form-data), оба эндпоинта одинаковые:**

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `data` | str | — (обязателен) | Что кодировать в QR (ссылка/текст) |
| `module_style` | str | `rounded` | `square` \| `rounded` \| `circle` \| `gapped` \| `vertical_bars` \| `horizontal_bars` |
| `fg_color` | str (hex) | `#000000` | Основной цвет |
| `fg_color2` | str (hex) | пусто | Второй цвет — если задан, включается градиент |
| `gradient` | str | `radial` | `radial` \| `horizontal` \| `vertical` \| `square` |
| `bg_color` | str (hex) или `transparent` | `#FFFFFF` | Цвет фона |
| `box_size` | int | `10` | Размер одного модуля в пикселях |
| `border` | int | `4` | Отступ в модулях (по стандарту — не меньше 4) |
| `error_correction` | str | `H` | `L`/`M`/`Q`/`H` — чем выше, тем устойчивее код к перекрытию (логотипом) |
| `logo` | file | — | PNG/JPEG для центра кода (опционально) |
| `logo_size_ratio` | float | `0.22` | Доля ширины QR под логотип |
| `rounded_logo` | bool | `true` | Круглая белая подложка под лого |

### Пример через curl

```bash
curl -X POST http://localhost:8000/generate \
  -F "data=https://example.com" \
  -F "module_style=rounded" \
  -F "fg_color=#1c1b1a" \
  -F "fg_color2=#e8a33d" \
  -F "gradient=radial" \
  -F "bg_color=#ffffff" \
  -F "logo=@logo.png" \
  -o qr.png
```

## Как это устроено

- `qr_core.py` — вся логика генерации: обёртка над `qrcode` +
  `StyledPilImage`, которая умеет форму модулей, градиентную заливку и
  вклейку логотипа с белой подложкой (через Pillow).
- `app.py` — тонкий HTTP-слой (FastAPI), два эндпоинта + отдача демо-страницы.
- `static/index.html` — простой фронт для ручного тестирования и подбора стиля.

## Важно про логотип

Чем крупнее логотип и выше плотность данных (длинная ссылка), тем выше риск,
что код перестанет сканироваться. Используйте `error_correction=H` при
вставке логотипа и не делайте `logo_size_ratio` больше `~0.25`. После
генерации всегда проверяйте код реальным сканером телефона.
