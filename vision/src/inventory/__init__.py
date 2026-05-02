"""Inventory layer: order queue, SKU bookkeeping, auto-replenish brain.

Sits on top of the vision/planning pipeline. Issues `Order` records
(source_shelf -> destination_shelf, qty units of sku) which the dispatcher
(added in a later phase) will execute via the closed-loop /execute/stream
endpoint.

Storage is sqlite for crash-safety; orders survive a backend restart.
"""
