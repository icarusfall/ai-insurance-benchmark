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
