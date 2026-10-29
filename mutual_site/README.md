# Mutually Assured AI Modelling: the site

A static site for the toy catastrophe model in `catmodel/`. The model runs in the browser (`public/model.js`, a port of the Python) so the levers are live.

- `python -m mutual_site.build` refreshes `public/data.js`: the defaults, the parameter registry, and the bio insurability tables.
- `python -m pytest tests/test_mutual_site.py` checks the JavaScript model against the Python one (needs Node).
- Local preview: `python -m http.server 8766 --directory mutual_site/public`.
- Railway: a second service from this repo with root directory `mutual_site`; the Dockerfile serves `public/` with Caddy on `$PORT`.
