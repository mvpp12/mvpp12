"""Build the profile cards from assets/portrait.webp and data.json.

Run:  python fetch_data.py && python generate.py
Needs Pillow. Writes four SVGs, one per card and theme:
  profile-dark.svg / profile-light.svg    photo scan + readout + live stats
  activity-dark.svg / activity-light.svg  contribution calendar scan
"""
import base64
import io
import json
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageEnhance, ImageOps

HERE = Path(__file__).parent
PORTRAIT = HERE / "assets" / "portrait.webp"
DATA = HERE / "data.json"

# Same tokens as mvpp12.github.io. "accent" fills shapes; "accent_text" is for lines and text.
THEMES = {
    "dark": dict(
        bg="#0b0d0b", panel="#101310", line="#262b25", line_strong="#394036",
        text="#eef0ea", text_2="#b6bcb1", muted="#8c9388",
        accent="#c6f24e", accent_text="#c6f24e", ink="#0b0d0b",
        ramp=["#1c211c", "#3d4a22", "#62792a", "#94b83a", "#c6f24e"],
        langs=["#c6f24e", "#94b83a", "#62792a", "#3d4a22"],
    ),
    "light": dict(
        bg="#f4f4ee", panel="#ebebe3", line="#dcddd3", line_strong="#c3c6b8",
        text="#12150f", text_2="#3c4238", muted="#5d6358",
        accent="#c6f24e", accent_text="#456400", ink="#12150f",
        ramp=["#e2e3da", "#dcef9e", "#c6f24e", "#8db32a", "#456400"],
        langs=["#c6f24e", "#8db32a", "#5c7d10", "#3c4238"],
    ),
}

W = 1000
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
    ("focus", "Applied AI · on-device machine learning"),
    ("award", "3rd Runner Up · PUP Hackathon 2026"),
    ("stack", "TensorFlow · Keras · TFLite · Python · Flutter"),
]


def nice_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def text(x, y, s, cls, extra=""):
    return f'<text x="{x}" y="{y}" class="{cls}"{extra}>{escape(str(s))}</text>'


def base_style(t):
    return f"""
.m{{font-family:{MONO}}} .s{{font-family:{SANS}}}
.hud{{font-size:11px;fill:{t['muted']};letter-spacing:.12em}}
.k{{font-size:11px;fill:{t['muted']};letter-spacing:.12em}}
.in{{opacity:0;animation:in .5s cubic-bezier(.22,1,.36,1) both}}
.live{{animation:blink 1.4s steps(1) infinite}}
.cur{{animation:blink 1s steps(1) infinite}}
@keyframes in{{from{{opacity:0;transform:translateX(-8px)}}to{{opacity:1;transform:none}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes blink{{50%{{opacity:0}}}}"""


def frame(t, h, label, path, synced):
    """Card background, grid texture and the HUD strip shared by both cards."""
    return f"""<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{t['line']}" stroke-width=".6" opacity=".55"/></pattern></defs>
<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="18" fill="{t['bg']}" stroke="{t['line']}"/>
<rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="17" fill="url(#grid)"/>
<g class="m">
<circle class="live" cx="40" cy="31" r="4.5" fill="{t['accent_text']}"/>
{text(54, 35, label, "hud")}
{text(54 + len(label) * 7.9 + 22, 35, path, "hud", f' fill="{t["text_2"]}"')}
{text(W - 32, 35, f"SYNCED {nice_date(synced).upper()}", "hud", ' text-anchor="end"')}
</g>
<path d="M24 50H{W - 24}" stroke="{t['line']}"/>"""


# ---------- Profile card ----------

def halftone():
    im = Image.open(PORTRAIT).convert("RGBA").crop(CROP)
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


def photo_uri(panel):
    """The real portrait, cropped like the halftone and flattened onto the panel colour."""
    im = Image.open(PORTRAIT).convert("RGBA").crop(CROP)
    im = im.resize((VW * 2, VH * 2), Image.LANCZOS)
    bg = Image.new("RGBA", im.size, panel)
    bg.alpha_composite(im)
    out = ImageEnhance.Contrast(bg.convert("RGB")).enhance(1.05)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def face_marks(x, y, w, h, n=16):
    return (f"M{x} {y + n}V{y}H{x + n}M{x + w - n} {y}H{x + w}V{y + n}"
            f"M{x + w} {y + h - n}V{y + h}H{x + w - n}M{x + n} {y + h}H{x}V{y + h - n}")


def profile_card(t, data, dots):
    H = 540
    fx, fy, fw, fh = FACE
    fx, fy = VX + fx, VY + fy
    br = 18  # viewfinder bracket length

    def bracket(x, y, dx, dy):
        return f'<path d="M{x} {y + dy * br}V{y}H{x + dx * br}"/>'

    rx = 440  # right column x
    dy = -28  # readout offset, keeps it centred beside the photo
    vx = rx + 104
    right = W - 40

    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Mark Vincent Plaza</title>
<desc id="d">Mark Vincent Plaza, aspiring AI engineer and IT student at PUP Sto. Tomas, training on-device machine-learning models and building the apps around them. {data['contributions_year']} contributions in the last year across {data['public_repos']} public repositories.</desc>
<style>{base_style(t)}
.name{{font-size:34px;font-weight:700;fill:{t['text']};letter-spacing:-.02em}}
.tag{{font-size:15px;fill:{t['text_2']}}}
.role{{font-size:11px;font-weight:600;fill:{t['accent_text']};letter-spacing:.12em}}
.v{{font-size:14px;fill:{t['text']}}}
.num{{font-size:30px;font-weight:700;fill:{t['text']};letter-spacing:-.02em}}
.num tspan{{font-size:16px;fill:{t['muted']};font-weight:600}}
.leg{{font-size:12px;fill:{t['text_2']}}}
.bar{{transform-box:fill-box;transform-origin:left;animation:grow .9s cubic-bezier(.22,1,.36,1) both}}
.dots{{animation:dots 2.2s ease both}}
.photo{{animation:fade 1s ease 1.1s both}}
.scan{{animation:scan 2.1s cubic-bezier(.4,0,.6,1) .1s both}}
.box{{opacity:0;animation:pop .4s ease 1.3s both}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes dots{{0%{{opacity:0}}25%{{opacity:1}}60%{{opacity:1}}100%{{opacity:0}}}}
@keyframes scan{{from{{transform:translateY(0)}}to{{transform:translateY({VH + 70}px)}}}}
@keyframes pop{{from{{opacity:0;transform:scale(1.06)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}.scan,.dots{{display:none}}}}
</style>
{frame(t, H, "SCANNING", "mvpp12 / profile", data['updated'])}
<defs>
<pattern id="pin" width="{STEP}" height="{STEP}" patternUnits="userSpaceOnUse" x="{VX}" y="{VY}"><circle cx="{STEP / 2}" cy="{STEP / 2}" r=".6" fill="{t['line_strong']}"/></pattern>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t['panel']}" stop-opacity="0"/><stop offset=".7" stop-color="{t['panel']}" stop-opacity=".92"/></linearGradient>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t['accent_text']}" stop-opacity="0"/><stop offset=".85" stop-color="{t['accent_text']}" stop-opacity=".16"/><stop offset="1" stop-color="{t['accent_text']}" stop-opacity=".9"/></linearGradient>
<clipPath id="vf"><rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" rx="10"/></clipPath>
</defs>

<!-- Viewfinder -->
<rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" rx="10" fill="{t['panel']}" stroke="{t['line']}"/>
<rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" fill="url(#pin)" clip-path="url(#vf)"/>
<image class="photo" href="{photo_uri(t['panel'])}" x="{VX}" y="{VY}" width="{VW}" height="{VH}" clip-path="url(#vf)" preserveAspectRatio="xMidYMid slice"/>
<g class="dots" fill="{t['accent_text']}" clip-path="url(#vf)">{dots}</g>
<g clip-path="url(#vf)"><rect class="scan" x="{VX}" y="{VY - 70}" width="{VW}" height="70" fill="url(#beam)"/></g>
<rect x="{VX}" y="{VY + VH - 64}" width="{VW}" height="64" fill="url(#fade)" clip-path="url(#vf)"/>
<g fill="none" stroke="{t['accent_text']}" stroke-width="2" stroke-linecap="round">
{bracket(VX + 12, VY + 12, 1, 1)}{bracket(VX + VW - 12, VY + 12, -1, 1)}
{bracket(VX + 12, VY + VH - 12, 1, -1)}{bracket(VX + VW - 12, VY + VH - 12, -1, -1)}
</g>
<g class="box" style="transform-origin:{fx + fw / 2}px {fy + fh / 2}px">
<path d="{face_marks(fx, fy, fw, fh)}" fill="none" stroke="{t['bg']}" stroke-width="5" stroke-linecap="round" opacity=".6"/>
<path d="{face_marks(fx, fy, fw, fh)}" fill="none" stroke="{t['accent']}" stroke-width="2" stroke-linecap="round"/>
</g>

<!-- Readout -->
<g class="in" style="animation-delay:.6s">
<rect x="{rx}" y="{84 + dy}" width="196" height="24" rx="12" fill="{t['accent']}" fill-opacity="{'.14' if t is THEMES['dark'] else '.35'}" stroke="{t['accent_text']}" stroke-opacity=".45"/>
<circle cx="{rx + 14}" cy="{96 + dy}" r="3.5" fill="{t['accent_text']}"/>
<text x="{rx + 25}" y="{100 + dy}" class="m role">ASPIRING AI ENGINEER</text>
</g>
<text x="{rx - 2}" y="{166 + dy}" class="s name in" style="animation-delay:.9s">Mark Vincent Plaza</text>
<text x="{rx}" y="{194 + dy}" class="s tag in" style="animation-delay:1.05s">Training on-device ML models and building the apps around them.</text>
"""]

    y = 238 + dy
    for i, (k, v) in enumerate(FIELDS):
        parts.append(
            f'<g class="in" style="animation-delay:{1.25 + i * 0.12:.2f}s">'
            f'<path d="M{rx} {y - 17}H{right}" stroke="{t["line"]}"/>'
            f'{text(rx, y, k.upper(), "m k")}{text(vx, y, v, "s v")}</g>'
        )
        y += 30
    parts.append(f'<path class="in" style="animation-delay:{1.25 + len(FIELDS) * 0.12:.2f}s" d="M{rx} {y - 17}H{right}" stroke="{t["line"]}"/>')

    # Live stats, refreshed daily by the workflow
    stats = [
        (data["contributions_year"], "", "CONTRIBUTIONS · 12 MO"),
        (data["public_repos"], "", "PUBLIC REPOS"),
        (data["longest_streak"], "d", "BEST STREAK"),
    ]
    col = (right - rx) / 3
    for i, (n, unit, label) in enumerate(stats):
        x = rx + i * col
        parts.append(
            f'<g class="in" style="animation-delay:{1.85 + i * 0.1:.2f}s">'
            f'<text x="{x}" y="{386 + dy}" class="s num">{n}<tspan dx="2">{unit}</tspan></text>'
            f'{text(x, 406 + dy, label, "m k")}</g>'
        )

    # Languages as one stacked bar, measured from repo code
    langs = data["languages"]
    total = sum(l["share"] for l in langs) or 1
    parts.append(f'<g class="in" style="animation-delay:2.2s">{text(rx, 440 + dy, "TOP LANGUAGES", "m k")}'
                 f'{text(right - 12, 440 + dy, "open to AI/ML internships", "m k", f" text-anchor=\"end\" fill=\"{t["accent_text"]}\"")}'
                 f'<rect class="cur" x="{right - 6}" y="{430 + dy}" width="7" height="12" fill="{t["accent_text"]}"/>'
                 f'<rect x="{rx}" y="{452 + dy}" width="{right - rx}" height="10" rx="5" fill="{t["line"]}"/></g>')
    bw = right - rx
    parts.append(f'<clipPath id="lb"><rect x="{rx}" y="{452 + dy}" width="{bw}" height="10" rx="5"/></clipPath><g clip-path="url(#lb)">')
    x = rx
    for i, l in enumerate(langs):
        w = bw * l["share"] / total
        parts.append(f'<rect class="bar" style="animation-delay:{2.3 + i * 0.12:.2f}s" x="{x:.1f}" y="{452 + dy}" width="{w:.1f}" height="10" fill="{t["langs"][i]}"/>')
        x += w
    parts.append("</g>")
    x = rx
    for i, l in enumerate(langs):
        label = f"{l['name']} {l['share'] * 100:.0f}%"
        parts.append(f'<g class="in" style="animation-delay:{2.4 + i * 0.1:.2f}s"><circle cx="{x + 5}" cy="{483 + dy}" r="4.5" fill="{t["langs"][i]}"/>'
                     f'{text(x + 15, 487 + dy, label, "m leg")}</g>')
        x += len(label) * 7.4 + 34

    parts.append("</svg>\n")
    return "\n".join(parts)


# ---------- Activity card ----------

def activity_card(t, data):
    H = 290
    days = data["days"]
    first = date.fromisoformat(days[0]["date"])
    cell, pitch = 13, 16
    weeks = (date.fromisoformat(days[-1]["date"]) - first).days // 7 + 1
    gx = W - 40 - (weeks * pitch - 3)
    gy = 132
    beam_w = 70
    sweep = 2.0  # seconds for the beam to cross the grid
    per_week = sweep / weeks

    active = [d for d in days if d["count"]]
    busiest = max(active, key=lambda d: d["count"]) if active else None

    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Contribution activity</title>
<desc id="d">{data['contributions_year']} contributions in the last 12 months over {len(active)} active days. Longest streak {data['longest_streak']} days.</desc>
<style>{base_style(t)}
.big{{font-size:26px;font-weight:700;fill:{t['text']};letter-spacing:-.02em}}
.big tspan{{font-size:15px;font-weight:400;fill:{t['text_2']};letter-spacing:0}}
.sv{{font-size:13px;fill:{t['text']};font-weight:600}}
.day{{font-size:10px;fill:{t['muted']}}}
.c{{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .35s cubic-bezier(.22,1,.36,1) both}}
.beam{{animation:sweep {sweep}s linear .3s both}}
@keyframes pop{{from{{opacity:0;transform:scale(.3)}}to{{opacity:1;transform:none}}}}
@keyframes sweep{{from{{transform:translateX(0);opacity:1}}95%{{opacity:1}}to{{transform:translateX({weeks * pitch + beam_w}px);opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}.beam{{display:none}}}}
</style>
{frame(t, H, "ACTIVITY SCAN", "mvpp12 / contributions", data['updated'])}
<defs><linearGradient id="beam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['accent_text']}" stop-opacity="0"/><stop offset=".85" stop-color="{t['accent_text']}" stop-opacity=".14"/><stop offset="1" stop-color="{t['accent_text']}" stop-opacity=".85"/></linearGradient></defs>

<text x="40" y="96" class="s big in" style="animation-delay:.1s">{data['contributions_year']}<tspan dx="8">contributions in the last 12 months</tspan></text>
"""]

    stats = [("ACTIVE DAYS", len(active)), ("BEST STREAK", f"{data['longest_streak']}d"), ("CURRENT", f"{data['current_streak']}d")]
    x = W - 40
    for i, (k, v) in enumerate(reversed(stats)):
        s = str(v)
        parts.append(f'<g class="in" style="animation-delay:{.2 + i * .08:.2f}s">'
                     f'{text(x, 96, s, "s sv", " text-anchor=\"end\"")}'
                     f'{text(x - len(s) * 8 - 8, 96, k, "m k", " text-anchor=\"end\"")}</g>')
        x -= len(s) * 8 + len(k) * 7.9 + 34

    # Month labels where a new month starts in the top row
    last_month = None
    for w in range(weeks):
        d = date.fromordinal(first.toordinal() + w * 7)
        if d.month != last_month and w < weeks - 2:
            parts.append(text(gx + w * pitch, gy - 10, f"{d:%b}", "m day"))
            last_month = d.month
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(text(gx - 10, gy + row * pitch + 10, name, "m day", ' text-anchor="end"'))

    base, lit = [], []
    for d in days:
        i = (date.fromisoformat(d["date"]) - first).days
        w, dow = divmod(i, 7)
        x, y = gx + w * pitch, gy + dow * pitch
        base.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3"/>')
        if d["level"]:
            lit.append(f'<rect class="c" style="animation-delay:{.3 + w * per_week:.2f}s" x="{x}" y="{y}" '
                       f'width="{cell}" height="{cell}" rx="3" fill="{t["ramp"][d["level"]]}"/>')
    parts.append(f'<g fill="{t["ramp"][0]}">{"".join(base)}</g>')
    parts.append("".join(lit))
    parts.append(f'<clipPath id="g"><rect x="{gx - 4}" y="{gy - 4}" width="{weeks * pitch + 5}" height="{7 * pitch + 5}"/></clipPath>'
                 f'<g clip-path="url(#g)"><rect class="beam" x="{gx - beam_w}" y="{gy - 4}" width="{beam_w}" height="{7 * pitch + 5}" fill="url(#beam)"/></g>')

    ly = gy + 7 * pitch + 26
    parts.append(f'<g class="m">{text(gx, ly + 10, "LESS", "k")}')
    for i, c in enumerate(t["ramp"]):
        parts.append(f'<rect x="{gx + 40 + i * pitch}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')
    parts.append(f'{text(gx + 48 + 5 * pitch, ly + 10, "MORE", "k")}')
    if busiest:
        parts.append(text(W - 40, ly + 10, f"BUSIEST DAY · {nice_date(busiest['date']).upper()} · {busiest['count']}", "k", ' text-anchor="end"'))
    parts.append("</g>\n</svg>\n")
    return "\n".join(parts)


if __name__ == "__main__":
    data = json.loads(DATA.read_text(encoding="utf-8"))
    dots = halftone()
    for name, t in THEMES.items():
        for kind, svg in (("profile", profile_card(t, data, dots)), ("activity", activity_card(t, data))):
            out = HERE / f"{kind}-{name}.svg"
            out.write_text(svg, encoding="utf-8")
            print(f"wrote {out.name} ({len(svg.encode()) / 1024:.0f} KB)")
