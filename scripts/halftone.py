"""Generate a halftone-style GitHub contribution graph (light + dark SVGs).

Each day is a dot; the dot grows with the number of contributions.
Uses only the Python standard library.
"""
import json
import math
import os
import urllib.request

USER = os.environ.get("USERNAME") or os.environ["GITHUB_REPOSITORY_OWNER"]
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_DIR = "profile-halftone"

# Palette pulled from hands.gif. Tweak freely.
THEMES = {
    "light": {
        "panel": "#d9d5cf",   # concrete
        "empty": "#bdb9b3",
        "dot": "#1c1512",     # ink
        "accent": "#8a5a44",  # deep skin shadow
        "text": "#5b5650",
    },
    "dark": {
        "panel": "#1c1512",
        "empty": "#332a25",
        "dot": "#bdb9b3",
        "accent": "#c79a82",  # skin
        "text": "#8f877f",
    },
}

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


def render(calendar, theme):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    nonzero = sorted(c for c in counts if c > 0)
    # Cap at the 95th percentile so one huge day doesn't flatten everything else
    cap = nonzero[int(len(nonzero) * 0.95) - 1] if nonzero else 1
    cap = max(cap, 1)

    cell, pad, caption_h = 16, 24, 26
    width = pad * 2 + len(weeks) * cell
    height = pad * 2 + 7 * cell + caption_h
    r_min, r_max = 1.6, cell / 2 - 0.6

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-label="{total} contributions in the last year">',
        f'<rect width="{width}" height="{height}" rx="10" fill="{theme["panel"]}"/>',
    ]

    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            c = day["contributionCount"]
            cx = pad + wi * cell + cell / 2
            cy = pad + day["weekday"] * cell + cell / 2
            if c == 0:
                parts.append(f'<circle cx="{cx}" cy="{cy}" r="1" fill="{theme["empty"]}"/>')
                continue
            ratio = min(c, cap) / cap
            r = r_min + (r_max - r_min) * math.sqrt(ratio)
            color = theme["accent"] if ratio >= 0.75 else theme["dot"]
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" fill="{color}">'
                f'<title>{day["date"]}: {c}</title></circle>'
            )

    parts.append(
        f'<text x="{pad}" y="{height - 12}" font-family="ui-monospace, Menlo, Consolas, monospace" '
        f'font-size="11" fill="{theme["text"]}">{total} contributions in the last year</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    calendar = fetch()
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(OUT_DIR, f"halftone-{name}.svg"), "w", encoding="utf-8") as f:
            f.write(render(calendar, theme))
    print(f"Wrote {len(THEMES)} SVGs to {OUT_DIR}/")


if __name__ == "__main__":
    main()
