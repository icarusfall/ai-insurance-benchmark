# Website

The public site: a static explainer (`public/index.html`), a failure gallery (`public/failures.html`), and the data they draw on (`public/data.js`, generated).

## Rebuild the data

```
python -m website.build
```

Runs the engine (about 3 minutes) and writes `public/data.js`: parameters, a sample world, ten seeds of every scripted strategy, a real briefing, and excerpts from local LLM run logs when `runs/` exists. Commit the result; deployment does not run the engine.

## Preview locally

```
python -m http.server 8765 --directory website/public
```

## Deploy on Railway

1. New service from the GitHub repo.
2. Settings: **Root directory** `website`. Railway finds the `Dockerfile` and builds a Caddy image that serves `public/` on `$PORT`.
3. Generate a domain. No environment variables or secrets are needed: the site is static and never calls a model.

The private control room (launching runs, spend) is a separate service and is not built yet.

## Play it yourself

`public/play.html` and `public/play.js` are a small browser game, written separately from the engine on purpose: three lines of business instead of client dossiers, twelve quarters, its own numbers, one bail-out and some hindsight. It teaches the same lessons (winner's curse, the long tail, reserving, claims handling, the hurdle) without reproducing the benchmark's mechanics. A house actuary plays the same world alongside the player. Balance, checked over 300 worlds: following the market and settling claims scores a median R of about 1.5; undercutting by 20% about 0.5; doing nothing 0.89.
