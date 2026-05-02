"""Direct tests for the OrderQueue (no FastAPI)."""
import pytest
from vision.src.inventory.orders import OrderQueue, OrderQueueError


@pytest.fixture
def queue(tmp_path):
    return OrderQueue(tmp_path / "orders.db")


def test_enqueue_assigns_id_and_pending_status(queue):
    o = queue.enqueue("widget", "shelf_A", "shelf_B", qty=2)
    assert o.id > 0
    assert o.status == "pending"
    assert o.qty == 2
    assert o.created_at > 0
    assert o.started_at is None
    assert o.finished_at is None


def test_enqueue_rejects_zero_qty(queue):
    with pytest.raises(OrderQueueError, match="positive"):
        queue.enqueue("w", "A", "B", qty=0)


def test_enqueue_rejects_same_source_and_destination(queue):
    with pytest.raises(OrderQueueError, match="differ"):
        queue.enqueue("w", "A", "A", qty=1)


def test_get_returns_what_was_enqueued(queue):
    o = queue.enqueue("widget", "A", "B", qty=1, reason="manual")
    fetched = queue.get(o.id)
    assert fetched.sku_id == "widget"
    assert fetched.reason == "manual"


def test_get_unknown_id_raises(queue):
    with pytest.raises(OrderQueueError, match="unknown"):
        queue.get(999)


def test_list_orders_newest_first(queue):
    o1 = queue.enqueue("w", "A", "B", qty=1)
    o2 = queue.enqueue("w", "A", "C", qty=1)
    o3 = queue.enqueue("w", "A", "D", qty=1)
    listed = queue.list_orders()
    assert [o.id for o in listed] == [o3.id, o2.id, o1.id]


def test_list_orders_filters_by_status(queue):
    o1 = queue.enqueue("w", "A", "B", qty=1)
    queue.enqueue("w", "A", "C", qty=1)
    queue.update_status(o1.id, "done")
    pending = queue.list_orders(status="pending")
    done = queue.list_orders(status="done")
    assert len(pending) == 1
    assert len(done) == 1
    assert done[0].id == o1.id


def test_next_pending_is_oldest(queue):
    o1 = queue.enqueue("w", "A", "B", qty=1)
    queue.enqueue("w", "A", "C", qty=1)
    queue.enqueue("w", "A", "D", qty=1)
    nxt = queue.next_pending()
    assert nxt is not None and nxt.id == o1.id


def test_next_pending_skips_done_orders(queue):
    o1 = queue.enqueue("w", "A", "B", qty=1)
    o2 = queue.enqueue("w", "A", "C", qty=1)
    queue.update_status(o1.id, "done")
    nxt = queue.next_pending()
    assert nxt is not None and nxt.id == o2.id


def test_next_pending_returns_none_when_empty(queue):
    assert queue.next_pending() is None


def test_update_status_to_running_sets_started_at(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    updated = queue.update_status(o.id, "running")
    assert updated.status == "running"
    assert updated.started_at is not None


def test_update_status_to_done_sets_finished_at(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    queue.update_status(o.id, "running")
    updated = queue.update_status(o.id, "done")
    assert updated.finished_at is not None


def test_update_status_terminal_state_blocks_further_changes(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    queue.update_status(o.id, "done")
    with pytest.raises(OrderQueueError, match="terminal"):
        queue.update_status(o.id, "pending")


def test_update_status_records_error_on_failed(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    queue.update_status(o.id, "running")
    failed = queue.update_status(o.id, "failed", error="robot stuck")
    assert failed.status == "failed"
    assert failed.error == "robot stuck"


def test_cancel_pending_order(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    cancelled = queue.cancel(o.id)
    assert cancelled.status == "cancelled"
    assert cancelled.finished_at is not None


def test_cancel_running_order_rejected(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    queue.update_status(o.id, "running")
    with pytest.raises(OrderQueueError, match="only pending"):
        queue.cancel(o.id)


def test_invalid_status_rejected(queue):
    o = queue.enqueue("w", "A", "B", qty=1)
    with pytest.raises(OrderQueueError, match="invalid status"):
        queue.update_status(o.id, "bogus")  # type: ignore[arg-type]


def test_sqlite_persists_across_queue_instances(tmp_path):
    db = tmp_path / "orders.db"
    q1 = OrderQueue(db)
    o = q1.enqueue("widget", "A", "B", qty=3)
    # Re-open the DB with a fresh queue object — order should still be there.
    q2 = OrderQueue(db)
    fetched = q2.get(o.id)
    assert fetched.sku_id == "widget" and fetched.qty == 3
