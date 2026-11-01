# Setup — Abhinav1480 profile README

Everything is built. This is the 10-minute checklist to make it live, plus a list
of things only you can verify.

## 1. Upload to `main`

Push this whole folder structure to the `main` branch of
`Abhinav1480/Abhinav1480` (the special profile repo):

```
README.md
SETUP.md
scripts/generate_svgs.py
assets/            (11 SVGs, all XML-validated)
.github/workflows/ (snake.yml, recent-activity.yml, profile-summary-cards.yml)
```

Or from PowerShell:

```powershell
cd "C:\Users\Abhi\Desktop\Abhinav1480-profile"
git init
git remote add origin https://github.com/Abhinav1480/Abhinav1480.git
git add -A
git commit -m "profile readme: dark crimson design system + activity workflows"
git branch -M main
git push -u origin main
```

## 2. Enable workflow write access

Settings → Actions → General → Workflow permissions → **Read and write permissions**.

All three workflows need `contents: write` (they commit SVGs / README changes).
They run as `github-actions[bot]`, which can push to `main` without a PAT.

## 3. Run each workflow once

Actions tab → pick each → **Run workflow**:

| Workflow | What it writes |
|---|---|
| `Generate contribution snake` | `assets/github-snake.svg` + `assets/github-snake-dark.svg` (overwrite placeholders) |
| `Update recent activity` | fills `<!--START_SECTION:activity-->` in README |
| `Generate profile summary cards` | `assets/summary-cards/*.svg` archive (README uses the live API images directly) |

Until the snake workflow runs, the snake shows a neutral placeholder — that's intentional.

## 4. Optional: port-folio mode

If you re-brand anything, edit `scripts/generate_svgs.py` copy and re-run it —
it re-checks every text string against its canvas width (Verdana metrics, a wide
fallback font) and refuses to write if anything overflows. Run from the repo root:

```powershell
python scripts/generate_svgs.py
```

That pipeline bakes the base state of each animation directly into the SVG, so a
renderer with no animation support still shows a complete, sensible image.

## What you must verify (I didn't guess these)

- **Gym Beast** — no public repo exists, so the card says "repo link coming soon". When you have one, search README.md for `<!-- // TODO: add repo link -->` and replace the placeholder link + `<sub>` row.
- **Sutradhar & Clinic Desk** — I described them exactly as "collaborative" and "hackathon project" with no role or win claims. If you want more detail (tech stack, what you built, team size), add it — I left `<!-- Please verify... -->` comments at each card.
- **AWS Tech Member '26 / AWS Cloud Club VJIT / Google Ambassador / AWS Student Community Day Hyderabad 2026** — used verbatim from your brief, badges only, no rank or role invented beyond the names themselves.
- **ExamOS live URL** — `https://exam-os-seven.vercel.app/` is from your brief; confirm it still deploys before recruiters click it.
- **Hackathon participation** — taken verbatim from your list. Only AIML Hacks KGRH is listed as a win (1st Place); the other seven are listed as *participated* only. If you place in any of those later, update the badge.

## Service choices & substitutions (verified live on Oct 31, 2026)

| Need | Chosen | Why |
|---|---|---|
| Contribution calendar | `github-profile-summary-cards` `profile-details` card (live API) | **`github-readme-activity-graph.vercel.app` is dead** (HTTP 402, DEPLOYMENT_DISABLED) |
| Streak stats | `streak-stats.demolab.com` (custom hex params) | live, theme-matched |
| Contribution snake | `Platane/snk@v3` | live; **needs the manual commit/push** I added to the workflow |
| Recent activity | `jamesgeorge007/github-activity-readme` | live, writes the README section itself |
| Profile views | `hits.dwyl.com/Abhinav1480/Abhinav1480.svg` | the only live counter found: komarev (404), profile-counter.glitch.me (410), visitcount.itsvg.in (404) |
| Icons | `skillicons.dev` | live, dark theme |

Every number on the profile comes from one of these live widgets — nothing was typed in
by hand. Where a service had no live counterpart, the element is a placeholder instead
of a fake stat.

## What does not animate the README

GitHub strips JavaScript and external CSS from rendered READMEs, so every animation
lives **inside the SVG files** (SMIL `<animate>` / `<animateTransform>`) and is loaded
through `<img>`. That's why nothing here depends on a theme toggle or a browser
extension. The custom SVGs also paint their own dark background rect, so they stay
readable in GitHub light mode.
