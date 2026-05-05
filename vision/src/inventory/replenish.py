"""Rule-based auto-replenish brain.

Walks the shelf list, finds shelves whose `inventory_count` has fallen
below a threshold (configurable per-shelf or globally), and queues refill
orders sourced from a designated *supplier* shelf for that SKU.

This is the simplest possible "AI" — no learning, no demand forecasting,
just "if low, refill". Good enough to demo end-to-end. The interface is
deliberately small so it can be swapped out for an RL policy later
(`replenish_plan` returns a list of orders the brain wants to issue;
swap the function body, leave the API).
"""
from __future__ import annotations
from dataclasses import dataclass
from vision.src.models import Shelf


# Default low-stock threshold as a fraction of capacity. Per-shelf overrides
# could be added to settings.yaml later — for the rule-based brain we keep
# it as a single number to avoid feature-creep before we have real data.
DEFAULT_THRESHOLD_FRACTION = 0.30


@dataclass(frozen=True)
class ReplenishProposal:
    """A single proposed order. Not yet enqueued — caller decides whether
    to actually push it onto the queue."""
    sku_id: str
    source_shelf_id: str
    destination_shelf_id: str
    qty: int
    reason: str


def replenish_plan(
    shelves: list[Shelf],
    threshold_fraction: float = DEFAULT_THRESHOLD_FRACTION,
) -> list[ReplenishProposal]:
    """Look at every tracked shelf and propose refills for low-stock ones.

    A shelf is "tracked" when it has both `sku_id` and `capacity > 0`.
    A "supplier" for a SKU is a shelf with the same `sku_id` and
    `inventory_count >= 1` (we read from it). The destination shelf is
    refilled up to its capacity. If multiple suppliers exist, the one
    with the most stock wins. Shelves with no supplier are skipped — the
    brain flags nothing rather than crash.
    """
    if not 0.0 < threshold_fraction <= 1.0:
        raise ValueError(
            f"threshold_fraction must be in (0, 1], got {threshold_fraction}"
        )

    # Group shelves by SKU for quick supplier lookup.
    by_sku: dict[str, list[Shelf]] = {}
    for s in shelves:
        if s.sku_id is None:
            continue
        by_sku.setdefault(s.sku_id, []).append(s)

    proposals: list[ReplenishProposal] = []
    for s in shelves:
        if s.sku_id is None or s.capacity <= 0:
            continue  # untracked / transit shelf
        threshold = s.capacity * threshold_fraction
        if s.inventory_count >= threshold:
            continue  # not low

        # Find the best supplier for this SKU: same sku_id, different shelf,
        # has stock to give. Pick the fullest one.
        candidates = [
            other for other in by_sku.get(s.sku_id, [])
            if other.id != s.id and other.inventory_count > 0
        ]
        if not candidates:
            continue  # no supplier available — humans need to restock manually
        supplier = max(candidates, key=lambda c: c.inventory_count)

        # How much to move: refill destination to capacity, but don't take
        # more than the supplier has.
        deficit = s.capacity - s.inventory_count
        qty = min(deficit, supplier.inventory_count)
        if qty <= 0:
            continue

        proposals.append(ReplenishProposal(
            sku_id=s.sku_id,
            source_shelf_id=supplier.id,
            destination_shelf_id=s.id,
            qty=qty,
            reason=(
                f"auto_replenish: shelf {s.id} ({s.inventory_count}/{s.capacity}) "
                f"below {threshold_fraction:.0%} threshold; refill from {supplier.id}"
            ),
        ))
    return proposals
