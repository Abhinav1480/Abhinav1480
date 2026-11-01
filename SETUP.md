# Setup — Abhinav1480 profile README

Everything is built. This is the 10-minute checklist to make it live, plus a list
of things only you can verify.

## Architecture (what makes this "3D")

Two layers, both from this same repo — no other repos involved:

1. **The README itself** — GitHub strips JavaScript and external CSS from rendered
   READMEs, so nothing in `README.md` can be a `<script>` or an iframe. Instead,
   `scripts/render3d.py` is a **real software 3D renderer** (numpy rotation
   matrices, perspective projection, back-face culling, painter depth sort,
   Lambert diffuse + Blinn specular + rim lighting). It renders each scene 36
   times across one rotation cycle and bakes the frames into one SVG as a SMIL
   flipbook (`<animate attributeName="opacity">` per frame group) — so the hero,
   the section dividers, the portal banner and the project-card numerals all
   show genuine rotating 3D geometry that animates inside GitHub's `<img>` tags.
   `scripts/generate_svgs.py` owns the non-3D SVGs (buttons, chips).
2. **The linked 3D experience** — `docs/index.html` is a self-contained
   Three.js/WebGL page (orbit-controlled crystal world, particles, shader grid
   floor, bloom) served by **GitHub Pages from this repo** at
   `abhinav1480.github.io/Abhinav1480`. The README's portal banner links to it.

## 1. Upload to `main`

Push this whole folder structure to the `main` branch of
`Abhinav1480/Abhinav1480` (the special profile repo):

```
README.md
SETUP.md
docs/index.html                        (WebGL 3D experience for GitHub Pages)
scripts/generate_svgs.py               (buttons, chips, non-3D SVGs)
scripts/render3d.py                    (the software 3D renderer → SMIL flipbooks)
assets/                                (17 SVGs, all XML-validated)
.github/workflows/                     (snake.yml, recent-activity.yml, profile-summary-cards.yml)
```

Or from PowerShell:

```powershell
cd "C:\Users\Abhi\Desktop\Abhinav1480-profile"
git init
git remote add origin https://github.com/Abhinav1480/Abhinav1480.git
git add -A
git commit -m "profile readme: 3D hero, WebGL experience, crimson design system"
git branch -M main
git push -u origin main
```

## 2. Enable GitHub Pages (for the 3D experience)

Settings → **Pages** → Source: **Deploy from a branch** → Branch: `main` /
`/docs` → Save. Live in ~1 minute at `https://abhinav1480.github.io/Abhinav1480/`.

The page loads Three.js r169 from the jsDelivr CDN; no build step, no local CSS.

## 3. Enable workflow write access

Settings → Actions → General → Workflow permissions → **Read and write permissions**.

All three workflows need `contents: write` (they commit SVGs / README changes).
They run as `github-actions[bot]`, which can push to `main` without a PAT.

If the workflow files are anywhere other than **repo-root** `.github/workflows/`,
Actions ignores them — that was the original bug (they lived one level too deep).

## 4. Run each workflow once

Actions tab → pick each → **Run workflow**:

| Workflow | What it writes |
|---|---|
| `Generate contribution snake` | `assets/github-snake.svg` + `assets/github-snake-dark.svg` (overwrite placeholders) |
| `Update recent activity` | fills `<!--START_SECTION:activity-->` in README |
| `Generate profile summary cards` | `assets/summary-cards/*.svg` archive (README uses the live API images directly) |

Until the snake workflow runs, the snake shows a neutral placeholder — that's intentional.

## 5. Re-branding

Edit the copy in `scripts/render3d.py` (3D scenes, hero, cards) or
`scripts/generate_svgs.py` (buttons, chips) and re-run. Both pipelines validate
every text string against its canvas width (Verdana metrics, a wide fallback
font) and refuse to write if anything overflows, and both bake the base state of
each animation into the SVG so a renderer with no animation support still shows a
complete image. Run from the repo root:

```powershell
python scripts/render3d.py          # regenerate all 3D SVGs into assets/
python scripts/render3d.py --preview# also write PNG previews of one frame each
python qa_bounds.py                 # numeric check: clusters stay on-canvas
```

## What you must verify (I didn't guess these)

- **Gym Beast** — no public repo exists, so the card says "repo link coming soon". When you have one, search README.md for `<!-- // TODO: add repo link -->` and replace the placeholder link + `<sub>` row.
- **Sutradhar & Clinic Desk** — I described them exactly as "collaborative" and "hackathon project" with no role or win claims. If you want more detail (tech stack, what you built, team size), add it — I left `<!-- Please verify... -->` comments at each card.
- **AWS Tech Member '26 / AWS Cloud Club VJIT / AWS Student Community Day Hyderabad 2026** — badges only, no rank or role invented beyond the names themselves.
- **ExamOS live URL** — `https://exam-os-seven.vercel.app/` is from your brief; confirm it still deploys before recruiters click it.
- **Hackathon list** — used verbatim from your list (SIH, HackIndia 2025 LIET UP West Regionals / Team Silent Eclipse, YUVAAN National AI/ML / Team Salaar, Replit Polaris Vibeathon, HackWithAI 2026 KLH Bachupally ACM, ACM VJIT AI Battle, ACM VJIT Re-designX). Only **AIML Hacks KGRH — 1st Place** is a win; the rest are participation only and are worded that way.
- **Tech stack** — every row is verbatim from your list (languages, frontend, backend, cloud & DevOps, design).

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
readable in GitHub light mode — and the WebGL layer is one click away via the portal
banner for anyone who wants the fully interactive version.
