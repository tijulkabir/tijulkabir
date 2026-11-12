"""Generate GitHub stats and top-language SVG cards for the profile README.

Usage: GITHUB_TOKEN=... python scripts/stats.py <username> <out_dir>
Uses only the standard library and the GitHub GraphQL API.
"""
import json
import os
import sys
import urllib.request
from html import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

BG, BORDER, RULE = "#080808", "#2b2b2b", "#242424"
ACCENT, TEXT, MUTED = "#7ee787", "#d4d4d4", "#8e8e8e"
FONT = "Segoe UI,Arial,sans-serif"


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def card(title, body, height):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}" '
        f'viewBox="0 0 480 {height}" role="img" aria-label="{escape(title)}">\n'
        f'<rect x="1" y="1" width="478" height="{height - 2}" rx="12" fill="{BG}" stroke="{BORDER}"/>\n'
        f'<g font-family="{FONT}">\n'
        f'<text x="24" y="38" font-size="18" font-weight="600" fill="{ACCENT}">{escape(title)}</text>\n'
        f'<path d="M24 54H456" stroke="{RULE}"/>\n{body}</g>\n</svg>\n'
    )


def stats_card(u):
    repos = u["repositories"]
    cc = u["contributionsCollection"]
    rows = [
        ("Total stars earned", sum(n["stargazerCount"] for n in repos["nodes"])),
        ("Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("Pull requests", u["pullRequests"]["totalCount"]),
        ("Issues", u["issues"]["totalCount"]),
        ("Public repositories", repos["totalCount"]),
        ("Contributed to (last year)", u["repositoriesContributedTo"]["totalCount"]),
    ]
    body = ""
    for i, (label, value) in enumerate(rows):
        y = 84 + i * 26
        body += (f'<text x="24" y="{y}" font-size="14" fill="{TEXT}">{escape(label)}</text>\n'
                 f'<text x="456" y="{y}" font-size="14" font-weight="600" fill="{ACCENT}" '
                 f'text-anchor="end">{value:,}</text>\n')
    return card("GitHub Stats", body, 84 + len(rows) * 26)


def langs_card(u, count=6):
    totals, colors = {}, {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            totals[name] = totals.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or MUTED
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:count]
    total = sum(v for _, v in top) or 1

    # stacked bar
    body, x, width = "", 24.0, 432.0
    body += f'<clipPath id="bar"><rect x="24" y="72" width="{width}" height="8" rx="4"/></clipPath>\n<g clip-path="url(#bar)">\n'
    for name, size in top:
        w = width * size / total
        body += f'<rect x="{x:.2f}" y="72" width="{w:.2f}" height="8" fill="{colors[name]}"/>\n'
        x += w
    body += "</g>\n"
    # two-column legend
    for i, (name, size) in enumerate(top):
        cx = 24 if i % 2 == 0 else 248
        y = 112 + (i // 2) * 26
        body += (f'<circle cx="{cx + 5}" cy="{y - 5}" r="5" fill="{colors[name]}"/>\n'
                 f'<text x="{cx + 18}" y="{y}" font-size="14" fill="{TEXT}">{escape(name)} '
                 f'<tspan fill="{MUTED}">{100 * size / total:.1f}%</tspan></text>\n')
    rows = (len(top) + 1) // 2
    return card("Most Used Languages", body, 112 + rows * 26 - 4)


def main():
    login, out = sys.argv[1], sys.argv[2]
    u = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(out, exist_ok=True)
    for fname, svg in (("stats.svg", stats_card(u)), ("top-langs.svg", langs_card(u))):
        with open(os.path.join(out, fname), "w", encoding="utf-8") as f:
            f.write(svg)
    print("wrote", out)


if __name__ == "__main__":
    main()
