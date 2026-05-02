"""SQLite-backed order queue.

Schema is one table — kept deliberately simple because the dispatcher only
needs FIFO pending lookup and per-id status updates. SQLite (rather than a
JSON file) because:
  - Atomic updates without lock-file dance.
  - Survives concurrent reads from multiple HTTP handlers without locking
    bugs (sqlite serializes writes via its WAL).
  - Future-proof: when you actually want history queries ("how many orders
    of SKU X completed last week?") you can write SQL directly.

The queue is process-local — there is no expectation of multiple servers
sharing a queue. If you ever run two backends against the same DB they'll
both see the same orders, but the dispatcher lock has to live in the
process, not the DB.
"""
from __future__ import annotations
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from vision.src.models import Order, OrderStatus


_VALID_STATUSES: tuple[OrderStatus, ...] = (
    "pending", "running", "done", "failed", "cancelled",
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id                TEXT    NOT NULL,
    source_shelf_id       TEXT    NOT NULL,
    destination_shelf_id  TEXT    NOT NULL,
    qty                   INTEGER NOT NULL,
    status                TEXT    NOT NULL,
    created_at            REAL    NOT NULL,
    started_at            REAL,
    finished_at           REAL,
    error                 TEXT,
    reason                TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_orders_status_created
    ON orders(status, created_at);
"""


class OrderQueueError(Exception):
    """Raised for application-level violations (unknown order id, bad
    status transition, etc.). Connection/IO failures are left as raw
    sqlite exceptions because they indicate something genuinely broken."""


class OrderQueue:
    """Thread-safe wrapper around the orders table.

    All public methods are safe to call from FastAPI request handlers or
    the dispatcher background loop concurrently. SQLite serializes the
    writes; we only add a single in-process lock around connection setup.
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._init_lock = threading.Lock()
        self._initialized = False

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.executescript(_SCHEMA)
                conn.commit()
            self._initialized = True

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        self._ensure_init()
        # check_same_thread=False so the dispatcher (background thread) can
        # share connections with FastAPI handlers. SQLite's GIL-equivalent
        # serializes the writes regardless.
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- Mutations ----------------------------------------------------------

    def enqueue(
        self,
        sku_id: str,
        source_shelf_id: str,
        destination_shelf_id: str,
        qty: int,
        reason: str = "",
    ) -> Order:
        """Append a new pending order. Returns the order with id assigned."""
        if qty <= 0:
            raise OrderQueueError(f"qty must be positive, got {qty}")
        if source_shelf_id == destination_shelf_id:
            raise OrderQueueError(
                f"source and destination must differ ({source_shelf_id})"
            )
        now = time.time()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO orders "
                "(sku_id, source_shelf_id, destination_shelf_id, qty, status, "
                "created_at, reason) "
                "VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                (sku_id, source_shelf_id, destination_shelf_id, qty, now, reason),
            )
            order_id = int(cur.lastrowid)
            # Read back inside the same connection — calling self.get() here
            # would open a fresh connection that doesn't see this transaction
            # until the outer context exits, leading to a phantom-miss.
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            return _row_to_order(row)

    def update_status(
        self,
        order_id: int,
        status: OrderStatus,
        error: str | None = None,
    ) -> Order:
        """Move an order to a new status. Sets started_at when going to
        'running' and finished_at when going to a terminal state."""
        if status not in _VALID_STATUSES:
            raise OrderQueueError(f"invalid status {status!r}")
        now = time.time()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT status FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            if row is None:
                raise OrderQueueError(f"unknown order id {order_id}")
            old = row["status"]
            if old in ("done", "failed", "cancelled") and status != old:
                raise OrderQueueError(
                    f"order {order_id} is in terminal state {old!r}; "
                    f"cannot transition to {status!r}"
                )
            sets = ["status = ?"]
            params: list = [status]
            if status == "running":
                sets.append("started_at = ?")
                params.append(now)
            if status in ("done", "failed", "cancelled"):
                sets.append("finished_at = ?")
                params.append(now)
            if error is not None:
                sets.append("error = ?")
                params.append(error)
            params.append(order_id)
            conn.execute(
                f"UPDATE orders SET {', '.join(sets)} WHERE id = ?",
                tuple(params),
            )
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            return _row_to_order(row)

    def cancel(self, order_id: int) -> Order:
        """Cancel a pending order. No-op (raises) if already running/done."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT status FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            if row is None:
                raise OrderQueueError(f"unknown order id {order_id}")
            if row["status"] != "pending":
                raise OrderQueueError(
                    f"only pending orders can be cancelled; order {order_id} "
                    f"is {row['status']!r}"
                )
        return self.update_status(order_id, "cancelled")

    # --- Reads --------------------------------------------------------------

    def get(self, order_id: int) -> Order:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            if row is None:
                raise OrderQueueError(f"unknown order id {order_id}")
            return _row_to_order(row)

    def list_orders(
        self,
        status: OrderStatus | None = None,
        limit: int = 100,
    ) -> list[Order]:
        """Return orders, newest first. Filter by status if specified."""
        with self._conn() as conn:
            if status is None:
                rows = conn.execute(
                    "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE status = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            return [_row_to_order(r) for r in rows]

    def next_pending(self) -> Order | None:
        """FIFO — oldest pending order, or None. Used by the dispatcher."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE status = 'pending' "
                "ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            return _row_to_order(row) if row else None


def _row_to_order(row: sqlite3.Row) -> Order:
    return Order(
        id=int(row["id"]),
        sku_id=str(row["sku_id"]),
        source_shelf_id=str(row["source_shelf_id"]),
        destination_shelf_id=str(row["destination_shelf_id"]),
        qty=int(row["qty"]),
        status=row["status"],
        created_at=float(row["created_at"]),
        started_at=float(row["started_at"]) if row["started_at"] is not None else None,
        finished_at=float(row["finished_at"]) if row["finished_at"] is not None else None,
        error=row["error"],
        reason=str(row["reason"] or ""),
    )
