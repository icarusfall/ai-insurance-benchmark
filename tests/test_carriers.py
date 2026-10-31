"""Who carries it: every carrier changes real settings, cites real sources, and pooling beats going alone."""
import dataclasses

import pytest

from catmodel import carriers
from catmodel.model import Settings
from mutual_site.build import registry


def test_carriers_change_real_settings_and_cite_real_sources():
    fields = {f.name for f in dataclasses.fields(Settings)}
    ids = {e["id"] for e in registry()}
    for c in carriers._defaults()["carriers"]:
        assert set(c["changes"]) <= fields, c["key"]
        assert set(c["sources"]) <= ids, c["key"]
        assert c["independence"] and c["incentive"] and c["capacity"]


def test_pooling_beats_a_captive_and_layers_carry_their_share():
    rows = {r["key"]: r for r in carriers.compare()}
    assert rows["captive"]["premium_per_lab"] > 2 * rows["mutual"]["premium_per_lab"]
    assert rows["commercial"]["premium_per_lab"] < rows["mutual"]["premium_per_lab"]
    assert rows["stack"]["carried"]["reinsurer"] > 0 and rows["backstop"]["carried"]["government"] > 0
    for r in rows.values():
        assert sum(r["carried"].values()) == pytest.approx(1.0)

