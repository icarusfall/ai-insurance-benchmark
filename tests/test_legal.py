"""Who pays: attribution is a chain of legal links, and the defaults match it."""
import pytest

from catmodel import legal
from catmodel.model import LEVELS, _pick


@pytest.mark.parametrize("level", LEVELS)
def test_peril_attribution_is_its_chain(level):
    d = legal._defaults()
    for peril in d["legal"]["attribution"]:
        assert _pick(d["perils"][peril]["attribution"], level) == pytest.approx(legal.chain(d, peril, level)["attribution"], rel=0.02)


def test_joint_liability_pays_everything_claimable_and_several_only_the_fault_share():
    d = legal._defaults()
    joint = legal.chain(d, "cyber_misuse", overrides=dict(liable=1, recoverable=1, joint=1, fault_share=0.1))
    several = legal.chain(d, "cyber_misuse", overrides=dict(liable=1, recoverable=1, joint=0, fault_share=0.1))
    assert joint["attribution"] == 1 and several["attribution"] == pytest.approx(0.1)


def test_every_scenario_names_real_links_and_sources():
    d = legal._defaults()
    from mutual_site.build import registry
    ids = {e["id"] for e in registry()}
    for sc in d["legal"]["scenarios"]:
        for peril, changes in sc["changes"].items():
            assert set(changes) <= {l["key"] for l in d["legal"]["attribution"][peril]}
        assert set(sc.get("sources", [])) <= ids
    for links in d["legal"]["attribution"].values():
        for l in links:
            assert set(l.get("sources", [])) <= ids
