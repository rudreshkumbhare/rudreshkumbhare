"""Generate a halftone-style GitHub contribution graph (light + dark SVGs).

Each day is a dot; the dot grows with the number of contributions.
Styled to match the pixel banner: black panel, cream ink, amber highlight.
Uses only the Python standard library.
"""
import json
import math
import os
import urllib.request

USER = os.environ.get("USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = "profile-halftone"

# Same black panel in both modes so it matches the banner above it.
# The dark variant only adds a hairline border so it separates from GitHub's dark page.
THEMES = {
    "light": {"panel": "#070707", "stroke": "none", "dither": 0.30},
    "dark": {"panel": "#070707", "stroke": "#2b2b2b", "dither": 0.22},
}

CREAM = "#ece6d6"
AMBER = "#f2a93b"
MUTED = "#8a8578"
EMPTY = "#ece6d6"

FONT = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "halftone-contrib",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def dot_radius(ratio, r_min, r_max):
    return r_min + (r_max - r_min) * math.sqrt(ratio)


def render(calendar, theme):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    nonzero = sorted(c for c in counts if c > 0)
    cap = nonzero[max(int(len(nonzero) * 0.95) - 1, 0)] if nonzero else 1
    cap = max(cap, 1)

    W, pad, gutter = 880, 36, 30
    cell = (W - pad * 2 - gutter) / len(weeks)
    r_min, r_max = 2.2, cell / 2 - 0.4

    strip_h = 12
    title_y = strip_h + 40
    month_y = title_y + 34
    grid_y = month_y + 14
    grid_bottom = grid_y + 7 * cell
    legend_y = grid_bottom + 26
    H = round(legend_y + 22)
    gx = pad + gutter

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="{total} contributions in the last year">',
        f'<rect width="{W}" height="{H}" fill="{theme["panel"]}"/>',
    ]
    if theme["stroke"] != "none":
        p.append(
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="none" '
            f'stroke="{theme["stroke"]}"/>'
        )

    # Dither strip along the top, echoing the banner
    sq = 6
    for row in range(2):
        for i in range(W // sq + 1):
            if (i + row) % 2 == 0:
                p.append(
                    f'<rect x="{i * sq}" y="{row * sq}" width="{sq}" height="{sq}" '
                    f'fill="{CREAM}" opacity="{theme["dither"]}"/>'
                )

    # Header
    p.append(
        f'<text x="{pad}" y="{title_y}" font-family="{FONT}" font-size="16" '
        f'letter-spacing="3" fill="{CREAM}">CONTRIBUTIONS</text>'
    )
    p.append(
        f'<text x="{W - pad}" y="{title_y}" text-anchor="end" font-family="{FONT}" '
        f'font-size="13" letter-spacing="2" fill="{AMBER}">{total} IN THE LAST YEAR</text>'
    )

    # Month labels
    last_month, last_x = None, -999
    for wi, week in enumerate(weeks):
        month = int(week["contributionDays"][0]["date"][5:7]) - 1
        if month != last_month:
            x = gx + wi * cell
            if x - last_x >= 34:
                p.append(
                    f'<text x="{x:.1f}" y="{month_y}" font-family="{FONT}" font-size="9" '
                    f'letter-spacing="1.5" fill="{MUTED}">{MONTHS[month]}</text>'
                )
                last_x = x
            last_month = month

    # Day labels
    for weekday, label in ((1, "MON"), (3, "WED"), (5, "FRI")):
        cy = grid_y + weekday * cell + cell / 2 + 3
        p.append(
            f'<text x="{pad}" y="{cy:.1f}" font-family="{FONT}" font-size="8" '
            f'letter-spacing="1" fill="{MUTED}">{label}</text>'
        )

    # Dots
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            c = day["contributionCount"]
            cx = gx + wi * cell + cell / 2
            cy = grid_y + day["weekday"] * cell + cell / 2
            if c == 0:
                p.append(
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.1" fill="{EMPTY}" opacity="0.22"/>'
                )
                continue
            ratio = min(c, cap) / cap
            color = AMBER if ratio >= 0.7 else CREAM
            p.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{dot_radius(ratio, r_min, r_max):.2f}" '
                f'fill="{color}"><title>{day["date"]}: {c}</title></circle>'
            )

    # Legend
    lx = W - pad
    p.append(
        f'<text x="{lx}" y="{legend_y + 3}" text-anchor="end" font-family="{FONT}" '
        f'font-size="9" letter-spacing="1.5" fill="{MUTED}">MORE</text>'
    )
    x = lx - 54
    for ratio, color in ((1.0, AMBER), (0.7, AMBER), (0.35, CREAM), (0.1, CREAM)):
        r = dot_radius(ratio, r_min, r_max)
        p.append(f'<circle cx="{x:.1f}" cy="{legend_y}" r="{r:.2f}" fill="{color}"/>')
        x -= r_max * 2 + 4
    p.append(
        f'<text x="{x - 2:.1f}" y="{legend_y + 3}" text-anchor="end" font-family="{FONT}" '
        f'font-size="9" letter-spacing="1.5" fill="{MUTED}">LESS</text>'
    )

    p.append("</svg>")
    return "\n".join(p)


def main():
    calendar = fetch()
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(OUT_DIR, f"halftone-{name}.svg"), "w", encoding="utf-8") as f:
            f.write(render(calendar, theme))
    print(f"Wrote {len(THEMES)} SVGs to {OUT_DIR}/")


if __name__ == "__main__":
    main()
