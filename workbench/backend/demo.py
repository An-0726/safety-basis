"""Deterministic synthetic fixture, never represented as an actual site photo."""
import io
from PIL import Image, ImageDraw, ImageFont


def demo_photo():
    image = Image.new('RGB', (960, 640), '#f1f5f9')
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 930, 610), outline='#64748b', width=3)
    draw.rounded_rectangle((370, 200, 580, 540), radius=65, fill='#b91c1c')
    draw.rectangle((443, 140, 507, 220), fill='#475569')
    draw.line((470, 150, 630, 150, 660, 270), fill='#1e293b', width=18)
    draw.ellipse((424, 224, 516, 316), fill='white', outline='#1e293b', width=4)
    draw.arc((435, 235, 505, 305), 185, 255, fill='#ef4444', width=9)
    draw.arc((435, 235, 505, 305), 255, 315, fill='#16a34a', width=9)
    draw.line((470, 270, 438, 258), fill='#0f172a', width=5)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 28)
        small = ImageFont.truetype('DejaVuSans.ttf', 20)
    except OSError:
        font = small = ImageFont.load_default()
    draw.text((60, 65), 'SYNTHETIC DEMO - NOT SITE EVIDENCE', fill='#0f172a', font=font)
    draw.text((60, 562), 'Inspection workflow sample / pressure indicator', fill='#334155', font=small)
    stream = io.BytesIO()
    image.save(stream, 'JPEG', quality=90)
    return stream.getvalue()
