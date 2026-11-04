"""Build profile.svg: a halftone "scan" of the portrait plus a classifier-style readout.

Run:  python generate.py
Needs Pillow. Reads assets/portrait.webp (transparent background), writes profile.svg.
"""
import base64
import io
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageEnhance, ImageOps

HERE = Path(__file__).parent
PORTRAIT = HERE / "assets" / "portrait.webp"
OUT = HERE / "profile.svg"

# Palette: same tokens as mvpp12.github.io (dark theme)
BG, PANEL, LINE, LINE_STRONG = "#0b0d0b", "#101310", "#262b25", "#394036"
TEXT, TEXT_2, MUTED, ACCENT = "#eef0ea", "#b6bcb1", "#8c9388", "#c6f24e"

W, H = 1000, 540
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
SANS = "'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"

# Viewfinder (left) geometry
VX, VY, VW, VH = 32, 64, 360, 432
STEP = 5.4  # halftone grid spacing

# Portrait crop (source pixels) and the face box inside the viewfinder
CROP = (110, 30, 790, 846)
FACE = (70, 36, 228, 300)

FIELDS = [
    ("studying", "BS Information Technology · PUP Sto. Tomas"),
    ("award", "3rd Runner Up · PUP Hackathon 2026"),
    ("stack", "Flutter · Dart · TensorFlow Lite · Java · Python · JS"),
    ("based", "Philippines"),
    ("site", "mvpp12.github.io"),
]

# Relative strengths only; no percentages on purpose
CLASSES = [("mobile_apps", 1.0), ("web_dev", 0.84), ("on_device_ml", 0.72)]


def halftone() -> str:
    im = Image.open(PORTRAIT).convert("RGBA")
    im = im.crop(CROP)

    cols, rows = int(VW // STEP), int(VH // STEP)
    small = im.resize((cols, rows), Image.LANCZOS)
    alpha = small.getchannel("A")
    lum = ImageOps.autocontrast(small.convert("L"), cutoff=1)

    max_r = STEP * 0.56
    dots = []
    for y in range(rows):
        for x in range(cols):
            a = alpha.getpixel((x, y)) / 255
            if a < 0.35:
                continue
            v = lum.getpixel((x, y)) / 255
            r = max_r * (0.24 + 0.76 * v ** 1.35) * min(1, a * 1.2)
            if r < 0.35:
                continue
            cx = VX + (x + 0.5) * (VW / cols)
            cy = VY + (y + 0.5) * (VH / rows)
            dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}"/>')
    return "".join(dots)


def photo_uri() -> str:
    """The real portrait, cropped like the halftone and flattened onto the panel colour."""
    im = Image.open(PORTRAIT).convert("RGBA").crop(CROP)
    im = im.resize((VW * 2, VH * 2), Image.LANCZOS)
    bg = Image.new("RGBA", im.size, PANEL)
    bg.alpha_composite(im)
    out = ImageEnhance.Contrast(bg.convert("RGB")).enhance(1.05)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def text(x, y, s, cls, extra=""):
    return f'<text x="{x}" y="{y}" class="{cls}"{extra}>{escape(s)}</text>'


def face_marks(x, y, w, h, n=16):
    return (f"M{x} {y + n}V{y}H{x + n}M{x + w - n} {y}H{x + w}V{y + n}"
            f"M{x + w} {y + h - n}V{y + h}H{x + w - n}M{x + n} {y + h}H{x}V{y + h - n}")


def build() -> str:
    fx, fy, fw, fh = FACE
    fx, fy = VX + fx, VY + fy
    br = 18  # viewfinder bracket length

    def bracket(x, y, dx, dy):
        return f'<path d="M{x} {y + dy * br}V{y}H{x + dx * br}"/>'

    rx = 440  # right column x
    kx, vx = rx, rx + 104

    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Mark Vincent Plaza</title>
<desc id="d">A halftone scan of Mark Vincent Plaza with a classifier-style readout: IT student at PUP Sto. Tomas building mobile apps, websites and on-device machine learning.</desc>
<style>
.m{{font-family:{MONO}}} .s{{font-family:{SANS}}}
.hud{{font-size:11px;fill:{MUTED};letter-spacing:.12em}}
.prompt{{font-size:13px;fill:{MUTED}}} .prompt tspan{{fill:{ACCENT}}}
.ok{{font-size:13px;fill:{ACCENT}}}
.name{{font-size:34px;font-weight:700;fill:{TEXT};letter-spacing:-.02em}}
.tag{{font-size:15px;fill:{TEXT_2}}}
.k{{font-size:11px;fill:{MUTED};letter-spacing:.12em}}
.v{{font-size:14px;fill:{TEXT}}}
.cls{{font-size:12.5px;fill:{TEXT_2}}}
.lbl{{font-size:11px;font-weight:600;fill:{BG}}}
.in{{opacity:0;animation:in .5s cubic-bezier(.22,1,.36,1) both}}
.bar{{transform-box:fill-box;transform-origin:left;animation:grow 1s cubic-bezier(.22,1,.36,1) both}}
.dots{{animation:dots 2.2s ease both}}
.photo{{animation:fade 1s ease 1.1s both}}
.scan{{animation:scan 2.1s cubic-bezier(.4,0,.6,1) .1s both}}
.box{{opacity:0;animation:pop .4s ease 1.3s both}}
.live{{animation:blink 1.4s steps(1) infinite}}
.cur{{animation:blink 1s steps(1) infinite}}
@keyframes in{{from{{opacity:0;transform:translateX(-8px)}}to{{opacity:1;transform:none}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes dots{{0%{{opacity:0}}25%{{opacity:1}}60%{{opacity:1}}100%{{opacity:0}}}}
@keyframes scan{{from{{transform:translateY(0)}}to{{transform:translateY({VH + 70}px)}}}}
@keyframes pop{{from{{opacity:0;transform:scale(1.06)}}to{{opacity:1;transform:none}}}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}.scan,.dots{{display:none}}}}
</style>
<defs>
<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{LINE}" stroke-width=".6" opacity=".55"/></pattern>
<pattern id="pin" width="{STEP}" height="{STEP}" patternUnits="userSpaceOnUse" x="{VX}" y="{VY}"><circle cx="{STEP / 2}" cy="{STEP / 2}" r=".6" fill="{LINE_STRONG}"/></pattern>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PANEL}" stop-opacity="0"/><stop offset=".7" stop-color="{PANEL}" stop-opacity=".92"/></linearGradient>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".85" stop-color="{ACCENT}" stop-opacity=".16"/><stop offset="1" stop-color="{ACCENT}" stop-opacity=".9"/></linearGradient>
<clipPath id="vf"><rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" rx="10"/></clipPath>
</defs>

<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="{BG}" stroke="{LINE}"/>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17" fill="url(#grid)"/>

<!-- HUD strip -->
<g class="m">
<circle class="live" cx="40" cy="31" r="4.5" fill="{ACCENT}"/>
{text(54, 35, "SCANNING", "hud")}
{text(140, 35, "mvpp12 / profile", "hud", f' fill="{TEXT_2}"')}
{text(W - 32, 35, "PH · UTC+8", "hud", ' text-anchor="end"')}
</g>
<path d="M24 50H{W - 24}" stroke="{LINE}"/>

<!-- Viewfinder -->
<rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" rx="10" fill="{PANEL}" stroke="{LINE}"/>
<rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" fill="url(#pin)" clip-path="url(#vf)"/>
<image class="photo" href="{photo_uri()}" x="{VX}" y="{VY}" width="{VW}" height="{VH}" clip-path="url(#vf)" preserveAspectRatio="xMidYMid slice"/>
<g class="dots" fill="{ACCENT}" clip-path="url(#vf)">{halftone()}</g>
<g clip-path="url(#vf)"><rect class="scan" x="{VX}" y="{VY - 70}" width="{VW}" height="70" fill="url(#beam)"/></g>
<rect x="{VX}" y="{VY + VH - 64}" width="{VW}" height="64" fill="url(#fade)" clip-path="url(#vf)"/>
<g fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round">
{bracket(VX + 12, VY + 12, 1, 1)}{bracket(VX + VW - 12, VY + 12, -1, 1)}
{bracket(VX + 12, VY + VH - 12, 1, -1)}{bracket(VX + VW - 12, VY + VH - 12, -1, -1)}
</g>
<g class="box" style="transform-origin:{fx + fw / 2}px {fy + fh / 2}px">
<path d="{face_marks(fx, fy, fw, fh)}" fill="none" stroke="{BG}" stroke-width="5" stroke-linecap="round" opacity=".6"/>
<path d="{face_marks(fx, fy, fw, fh)}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round"/>
<rect x="{fx - 1}" y="{fy + fh + 6}" width="120" height="20" rx="5" fill="{ACCENT}"/>
<text x="{fx + 7}" y="{fy + fh + 20}" class="m lbl">class: developer</text>
</g>
<g class="m">
{text(VX + 20, VY + VH - 22, "FRAME 001", "hud")}
{text(VX + VW - 20, VY + VH - 22, "f/1.8 · 1/120", "hud", ' text-anchor="end"')}
</g>

<!-- Readout -->
<text x="{rx}" y="92" class="m prompt in" style="animation-delay:.2s"><tspan>$</tspan> scan --subject mvpp12</text>
<text x="{rx}" y="116" class="m ok in" style="animation-delay:.6s">✓ subject detected · profile loaded</text>
<text x="{rx - 2}" y="166" class="s name in" style="animation-delay:.9s">Mark Vincent Plaza</text>
<text x="{rx}" y="194" class="s tag in" style="animation-delay:1.05s">IT student building mobile apps, websites &amp; on-device ML.</text>
"""]

    y = 238
    for i, (k, v) in enumerate(FIELDS):
        d = 1.25 + i * 0.12
        parts.append(
            f'<g class="in" style="animation-delay:{d:.2f}s">'
            f'<path d="M{rx} {y - 17}H{W - 40}" stroke="{LINE}"/>'
            f'{text(kx, y, k.upper(), "m k")}{text(vx, y, v, "s v")}</g>'
        )
        y += 30
    parts.append(f'<path class="in" style="animation-delay:{1.25 + len(FIELDS) * 0.12:.2f}s" d="M{rx} {y - 17}H{W - 40}" stroke="{LINE}"/>')

    y += 14
    parts.append(f'<g class="in" style="animation-delay:2s">{text(kx, y, "TOP CLASSES", "m k")}'
                 f'{text(W - 40, y, "open to opportunities", "m k", f" text-anchor=\"end\" fill=\"{ACCENT}\"")}'
                 f'<rect class="cur" x="{W - 36}" y="{y - 10}" width="7" height="12" fill="{ACCENT}"/></g>')
    bar_x, bar_w = rx + 132, W - 40 - (rx + 132)
    for i, (name, strength) in enumerate(CLASSES):
        y += 26
        d = 2.15 + i * 0.15
        parts.append(
            f'<g class="in" style="animation-delay:{d:.2f}s">{text(kx, y, name, "m cls")}'
            f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="10" rx="5" fill="{LINE}"/></g>'
            f'<rect class="bar" style="animation-delay:{d + 0.1:.2f}s" x="{bar_x}" y="{y - 10}" '
            f'width="{bar_w * strength:.1f}" height="10" rx="5" fill="{ACCENT}" opacity="{1 - i * 0.22:.2f}"/>'
        )

    parts.append("</svg>\n")
    return "\n".join(parts)


if __name__ == "__main__":
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT} ({len(svg.encode()) / 1024:.0f} KB)")
