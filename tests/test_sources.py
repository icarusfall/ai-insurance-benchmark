"""The parameter registry stays well formed: unique ids, required fields, known vocabularies."""
import glob
import os

import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..", "catmodel", "sources")
REQUIRED = {"id", "peril", "informs", "lens", "claim", "values", "source", "accessed", "status"}
PERILS = {"cyber", "bio", "ip", "all", "structure"}
LENSES = {"scratch", "parallel", "market", "expert"}
STATUSES = {"verified", "secondary", "unverified"}


def entries():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.yaml"))):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):                       # market_snapshot.yaml is data, not registry entries
            out += [(os.path.basename(path), e) for e in data]
    return out


def test_registry_is_well_formed():
    es = entries()
    assert es
    ids = [e["id"] for _, e in es]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for name, e in es:
        assert REQUIRED <= set(e), f"{name}:{e.get('id')} missing {REQUIRED - set(e)}"
        assert e["peril"] in PERILS and e["lens"] in LENSES and e["status"] in STATUSES, f"{name}:{e['id']}"
        assert e["source"].get("url", "").startswith("https://"), f"{name}:{e['id']} needs a source url"
