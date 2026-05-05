"""FastAPI tests for /orders, /inventory, /replenish endpoints."""
import json


# --- /inventory -------------------------------------------------------------

def test_inventory_returns_shelves_and_skus(client, tmp_config):
    # conftest's shelves.json has 3 untracked shelves (no sku_id) by default.
    # Replace with a tracked layout via PUT /shelves.
    payload = {
        "shelves": [
            {
                "id": "supplier", "x_m": 0.5, "y_m": 0.5,
                "width_m": 0.3, "length_m": 0.3, "rotation_deg": 0,
                "approach_point": {"x_m": 0.5, "y_m": 1.0, "heading_deg": 90},
                "sku_id": "widget", "inventory_count": 10, "capacity": 10,
            },
            {
                "id": "store", "x_m": 1.5, "y_m": 0.5,
                "width_m": 0.3, "length_m": 0.3, "rotation_deg": 0,
                "approach_point": {"x_m": 1.5, "y_m": 1.0, "heading_deg": 90},
                "sku_id": "widget", "inventory_count": 2, "capacity": 10,
            },
        ]
    }
    client.put("/api/shelves", json=payload)
    r = client.get("/api/inventory")
    assert r.status_code == 200
    data = r.json()
    assert {s["shelf_id"] for s in data["shelves"]} == {"supplier", "store"}
    assert len(data["skus"]) == 1
    sku = data["skus"][0]
    assert sku["sku_id"] == "widget"
    assert sku["total"] == 12
    assert sku["capacity"] == 20


def test_inventory_omits_untracked_shelves_from_skus(client):
    # Default conftest shelves have no sku_id -> shelves listed, skus empty.
    r = client.get("/api/inventory")
    assert r.status_code == 200
    data = r.json()
    assert len(data["shelves"]) >= 1
    assert data["skus"] == []


# --- /orders ----------------------------------------------------------------

def test_create_order_assigns_id_and_returns_pending(client):
    r = client.post("/api/orders", json={
        "sku_id": "widget", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B", "qty": 2,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["id"] > 0
    assert data["status"] == "pending"
    assert data["qty"] == 2


def test_create_order_rejects_unknown_shelf(client):
    r = client.post("/api/orders", json={
        "sku_id": "widget", "source_shelf_id": "ghost",
        "destination_shelf_id": "shelf_B", "qty": 1,
    })
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "unknown_shelf"


def test_create_order_rejects_zero_qty(client):
    r = client.post("/api/orders", json={
        "sku_id": "widget", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B", "qty": 0,
    })
    assert r.status_code == 400


def test_list_orders_returns_newest_first(client):
    a = client.post("/api/orders", json={
        "sku_id": "w", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B", "qty": 1,
    }).json()
    b = client.post("/api/orders", json={
        "sku_id": "w", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_C", "qty": 1,
    }).json()
    r = client.get("/api/orders")
    ids = [o["id"] for o in r.json()["orders"]]
    assert ids[:2] == [b["id"], a["id"]]


def test_list_orders_filter_by_status(client):
    a = client.post("/api/orders", json={
        "sku_id": "w", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B", "qty": 1,
    }).json()
    client.delete(f"/api/orders/{a['id']}")  # cancel
    pending = client.get("/api/orders?status=pending").json()["orders"]
    cancelled = client.get("/api/orders?status=cancelled").json()["orders"]
    assert all(o["status"] == "pending" for o in pending)
    assert any(o["id"] == a["id"] for o in cancelled)


def test_list_orders_invalid_status_400(client):
    r = client.get("/api/orders?status=bogus")
    assert r.status_code == 400


def test_get_order_by_id(client):
    a = client.post("/api/orders", json={
        "sku_id": "widget", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B", "qty": 5,
    }).json()
    r = client.get(f"/api/orders/{a['id']}")
    assert r.status_code == 200
    assert r.json()["sku_id"] == "widget"


def test_get_unknown_order_404(client):
    r = client.get("/api/orders/9999")
    assert r.status_code == 404


def test_cancel_pending_order(client):
    a = client.post("/api/orders", json={
        "sku_id": "w", "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B", "qty": 1,
    }).json()
    r = client.delete(f"/api/orders/{a['id']}")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_unknown_order_404(client):
    r = client.delete("/api/orders/9999")
    assert r.status_code == 404


# --- /replenish/preview + /replenish/run -----------------------------------

def _put_replenish_layout(client):
    """Set up a layout where store needs a refill from supplier."""
    payload = {
        "shelves": [
            {
                "id": "supplier", "x_m": 0.5, "y_m": 0.5,
                "width_m": 0.3, "length_m": 0.3, "rotation_deg": 0,
                "approach_point": {"x_m": 0.5, "y_m": 1.0, "heading_deg": 90},
                "sku_id": "widget", "inventory_count": 10, "capacity": 10,
            },
            {
                "id": "store", "x_m": 1.5, "y_m": 0.5,
                "width_m": 0.3, "length_m": 0.3, "rotation_deg": 0,
                "approach_point": {"x_m": 1.5, "y_m": 1.0, "heading_deg": 90},
                "sku_id": "widget", "inventory_count": 1, "capacity": 10,
            },
        ]
    }
    client.put("/api/shelves", json=payload)


def test_replenish_preview_returns_proposals_without_creating_orders(client):
    _put_replenish_layout(client)
    r = client.post("/api/replenish/preview", json={})
    assert r.status_code == 200
    proposals = r.json()["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["destination_shelf_id"] == "store"
    # Verify no orders were actually created.
    listed = client.get("/api/orders").json()["orders"]
    assert listed == []


def test_replenish_run_creates_orders(client):
    _put_replenish_layout(client)
    r = client.post("/api/replenish/run", json={})
    assert r.status_code == 200
    body = r.json()
    assert len(body["enqueued"]) == 1
    assert body["skipped"] == []
    # And the order is now in the queue.
    listed = client.get("/api/orders").json()["orders"]
    assert any(o["destination_shelf_id"] == "store" for o in listed)


def test_replenish_run_skips_duplicate_pending_order(client):
    _put_replenish_layout(client)
    client.post("/api/replenish/run", json={})  # first pass enqueues
    second = client.post("/api/replenish/run", json={}).json()
    # Second pass should skip because the order is already pending.
    assert second["enqueued"] == []
    assert len(second["skipped"]) == 1


def test_replenish_invalid_threshold_400(client):
    r = client.post("/api/replenish/preview", json={"threshold_fraction": 1.5})
    assert r.status_code == 400


# --- Shelf save/load round-trip with inventory fields ---------------------

def test_shelves_round_trip_preserves_sku_fields(client):
    payload = {
        "shelves": [
            {
                "id": "tracked", "x_m": 0.5, "y_m": 0.5,
                "width_m": 0.3, "length_m": 0.3, "rotation_deg": 0,
                "approach_point": {"x_m": 0.5, "y_m": 1.0, "heading_deg": 90},
                "sku_id": "widget", "inventory_count": 7, "capacity": 12,
            }
        ]
    }
    r = client.put("/api/shelves", json=payload)
    assert r.status_code == 200
    fetched = client.get("/api/shelves").json()["shelves"]
    s = next(x for x in fetched if x["id"] == "tracked")
    # GET /api/shelves currently returns only the planning fields, not SKU
    # fields — that's fine for the layout editor. But /api/inventory must
    # see them, since it reads from the same JSON.
    inv = client.get("/api/inventory").json()
    tracked_inv = next(x for x in inv["shelves"] if x["shelf_id"] == "tracked")
    assert tracked_inv["sku_id"] == "widget"
    assert tracked_inv["inventory_count"] == 7
    assert tracked_inv["capacity"] == 12
