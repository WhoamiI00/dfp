"""Tests for the rule-based auto-replenish brain."""
import pytest
from vision.src.models import Shelf, ApproachPoint
from vision.src.inventory.replenish import replenish_plan


def _shelf(
    id: str, sku_id: str | None = None, count: int = 0, capacity: int = 0,
) -> Shelf:
    return Shelf(
        id=id, x_m=0, y_m=0, width_m=0.3, length_m=0.3, rotation_deg=0,
        approach_point=ApproachPoint(x_m=0, y_m=0, heading_deg=0),
        sku_id=sku_id, inventory_count=count, capacity=capacity,
    )


def test_no_proposals_when_no_shelves_tracked():
    assert replenish_plan([_shelf("A"), _shelf("B")]) == []


def test_no_proposals_when_all_shelves_full():
    shelves = [
        _shelf("supplier", "widget", count=10, capacity=10),
        _shelf("dest", "widget", count=10, capacity=10),
    ]
    assert replenish_plan(shelves) == []


def test_proposes_refill_when_destination_below_threshold():
    shelves = [
        _shelf("supplier", "widget", count=20, capacity=20),
        _shelf("dest", "widget", count=2, capacity=10),  # 20% < 30% default
    ]
    proposals = replenish_plan(shelves)
    assert len(proposals) == 1
    p = proposals[0]
    assert p.sku_id == "widget"
    assert p.source_shelf_id == "supplier"
    assert p.destination_shelf_id == "dest"
    assert p.qty == 8  # refill to capacity (10 - 2)


def test_qty_capped_by_supplier_stock():
    shelves = [
        _shelf("supplier", "widget", count=3, capacity=20),
        _shelf("dest", "widget", count=0, capacity=10),
    ]
    proposals = replenish_plan(shelves)
    assert len(proposals) == 1
    assert proposals[0].qty == 3  # supplier only has 3


def test_no_proposal_when_no_supplier_for_sku():
    shelves = [
        _shelf("dest", "widget", count=0, capacity=10),  # alone, no supplier
        _shelf("other", "gadget", count=10, capacity=10),
    ]
    assert replenish_plan(shelves) == []


def test_picks_fullest_supplier_when_multiple_available():
    shelves = [
        _shelf("low", "widget", count=2, capacity=20),
        _shelf("medium", "widget", count=8, capacity=20),
        _shelf("full", "widget", count=15, capacity=20),
        _shelf("dest", "widget", count=0, capacity=10),
    ]
    proposals = replenish_plan(shelves)
    # Note: "full" is at 75% (above 30% threshold) so it's fine; "medium"
    # is at 40% so also fine; "low" is at 10% so IT will trigger a refill
    # proposal too. Check what we got and find the proposal for "dest".
    dest_props = [p for p in proposals if p.destination_shelf_id == "dest"]
    assert len(dest_props) == 1
    assert dest_props[0].source_shelf_id == "full"  # most stock wins


def test_proposes_one_per_low_shelf():
    shelves = [
        _shelf("supplier", "widget", count=50, capacity=50),
        _shelf("low_a", "widget", count=1, capacity=10),
        _shelf("low_b", "widget", count=2, capacity=10),
    ]
    proposals = replenish_plan(shelves)
    assert len(proposals) == 2
    dests = {p.destination_shelf_id for p in proposals}
    assert dests == {"low_a", "low_b"}


def test_threshold_fraction_changes_what_counts_as_low():
    shelves = [
        _shelf("supplier", "widget", count=20, capacity=20),
        _shelf("dest", "widget", count=4, capacity=10),  # 40%
    ]
    # At 30% threshold: 40% is fine, no proposal.
    assert replenish_plan(shelves, threshold_fraction=0.30) == []
    # At 50% threshold: 40% is low, expect proposal.
    assert len(replenish_plan(shelves, threshold_fraction=0.50)) == 1


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        replenish_plan([], threshold_fraction=0)
    with pytest.raises(ValueError):
        replenish_plan([], threshold_fraction=1.5)
    with pytest.raises(ValueError):
        replenish_plan([], threshold_fraction=-0.1)


def test_proposal_reason_mentions_threshold_and_supplier():
    shelves = [
        _shelf("supplier", "widget", count=20, capacity=20),
        _shelf("dest", "widget", count=1, capacity=10),
    ]
    proposals = replenish_plan(shelves)
    reason = proposals[0].reason
    assert "auto_replenish" in reason
    assert "supplier" in reason
    assert "dest" in reason
