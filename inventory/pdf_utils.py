import io
import re
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ARABIC_FONT_NAME = 'ArabicFont'
_FONT_REGISTERED = False

ARABIC_TEXT_RE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s]+'
)


def _font_candidates():
    return [
        Path(r'C:\Windows\Fonts\tahoma.ttf'),
        Path(r'C:\Windows\Fonts\arial.ttf'),
        settings.BASE_DIR / 'static' / 'fonts' / 'Amiri-Regular.ttf',
    ]


def get_arabic_font_path():
    for path in _font_candidates():
        if path.exists():
            return path
    return None


def register_arabic_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return ARABIC_FONT_NAME

    font_path = get_arabic_font_path()
    if not font_path:
        return 'Helvetica'

    pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, str(font_path)))
    _FONT_REGISTERED = True
    return ARABIC_FONT_NAME


def shape_arabic(text):
    if text is None:
        return ''
    text = str(text).strip()
    if not text:
        return text
    if not any('\u0600' <= char <= '\u06FF' for char in text):
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def reshape_html_arabic(html):
    def replace_match(match):
        return shape_arabic(match.group(0))

    return ARABIC_TEXT_RE.sub(replace_match, html)


def build_pdf_styles(font_name):
    return f"""
    @page {{
        size: A4;
        margin: 1.5cm;
    }}
    body {{
        font-family: '{font_name}';
        direction: rtl;
        text-align: right;
        font-size: 12px;
        color: #111;
    }}
    h2 {{
        text-align: center;
        margin-bottom: 16px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
    }}
    th, td {{
        border: 1px solid #333;
        padding: 6px 8px;
        text-align: right;
    }}
    th {{
        background: #eee;
    }}
    """


def render_arabic_pdf(html_content):
    font_name = register_arabic_font()
    shaped_html = reshape_html_arabic(html_content)
    styles = build_pdf_styles(font_name)

    if '</head>' in shaped_html:
        shaped_html = shaped_html.replace('</head>', f'<style>{styles}</style></head>', 1)
    else:
        shaped_html = f'<html><head><meta charset="UTF-8"><style>{styles}</style></head>{shaped_html}</html>'

    from xhtml2pdf import pisa

    result = io.BytesIO()
    pdf_status = pisa.CreatePDF(
        shaped_html,
        dest=result,
        encoding='utf-8',
    )
    if pdf_status.err:
        return None
    return result.getvalue()