"use client";
import { useCallback, useEffect, useState } from "react";
import {
  getInventory, listOrders, createOrder, cancelOrder,
  previewReplenish, runReplenish,
  type ShelfInventory, type SkuTotal, type Order, type ReplenishProposal,
} from "../lib/api";
import { getShelves } from "../lib/api";
import type { Shelf } from "../lib/types";

const REFRESH_MS = 2000;

export default function InventoryTab() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [shelfInv, setShelfInv] = useState<ShelfInventory[]>([]);
  const [skus, setSkus] = useState<SkuTotal[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [proposals, setProposals] = useState<ReplenishProposal[] | null>(null);
  const [message, setMessage] = useState("");

  // New-order form state
  const [newSku, setNewSku] = useState("widget");
  const [newSrc, setNewSrc] = useState("");
  const [newDst, setNewDst] = useState("");
  const [newQty, setNewQty] = useState(1);
  const [thresholdPct, setThresholdPct] = useState(30);

  const refresh = useCallback(async () => {
    try {
      const [inv, ord, sh] = await Promise.all([
        getInventory(),
        listOrders(),
        getShelves(),
      ]);
      setShelfInv(inv.shelves);
      setSkus(inv.skus);
      setOrders(ord.orders);
      setShelves(sh.shelves);
      if (sh.shelves.length >= 1 && !newSrc) setNewSrc(sh.shelves[0].id);
      if (sh.shelves.length >= 2 && !newDst) setNewDst(sh.shelves[1].id);
    } catch (e) {
      setMessage(`Refresh failed: ${e}`);
    }
  }, [newSrc, newDst]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const handleCreate = async () => {
    if (!newSrc || !newDst || newSrc === newDst) {
      setMessage("Pick two different shelves.");
      return;
    }
    try {
      const o = await createOrder({
        sku_id: newSku, source_shelf_id: newSrc,
        destination_shelf_id: newDst, qty: newQty,
        reason: "manual",
      });
      setMessage(`Order #${o.id} queued.`);
      refresh();
    } catch (e) {
      setMessage(`Create failed: ${e}`);
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await cancelOrder(id);
      setMessage(`Order #${id} cancelled.`);
      refresh();
    } catch (e) {
      setMessage(`Cancel failed: ${e}`);
    }
  };

  const handlePreview = async () => {
    try {
      const r = await previewReplenish(thresholdPct / 100);
      setProposals(r.proposals);
      setMessage(
        r.proposals.length === 0
          ? "Brain says: nothing to refill."
          : `Brain proposes ${r.proposals.length} refill order(s) — review below.`,
      );
    } catch (e) {
      setMessage(`Preview failed: ${e}`);
    }
  };

  const handleRun = async () => {
    try {
      const r = await runReplenish(thresholdPct / 100);
      setProposals(null);
      const skipped = r.skipped.length;
      const enqueued = r.enqueued.length;
      setMessage(
        `Enqueued ${enqueued} order(s)` +
        (skipped ? `, skipped ${skipped} duplicate(s).` : "."),
      );
      refresh();
    } catch (e) {
      setMessage(`Run failed: ${e}`);
    }
  };

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Left: stock per shelf + per SKU */}
      <div className="col-span-4 space-y-4">
        <div>
          <h3 className="font-bold mb-2">Stock per shelf</h3>
          <table className="w-full text-sm">
            <thead className="text-white/60 border-b border-white/10">
              <tr><th className="text-left">Shelf</th><th className="text-left">SKU</th><th className="text-right">Stock</th></tr>
            </thead>
            <tbody>
              {shelfInv.map(s => {
                const pct = s.capacity > 0 ? Math.round((s.inventory_count / s.capacity) * 100) : 0;
                const low = s.capacity > 0 && pct < thresholdPct;
                return (
                  <tr key={s.shelf_id} className="border-b border-white/5">
                    <td>{s.shelf_id}</td>
                    <td className="text-white/70">{s.sku_id ?? "—"}</td>
                    <td className={`text-right ${low ? "text-amber-400" : ""}`}>
                      {s.inventory_count}/{s.capacity}
                      {low && " ⚠"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div>
          <h3 className="font-bold mb-2">Stock per SKU</h3>
          {skus.length === 0 ? (
            <div className="text-sm text-white/50">No tracked SKUs. Set sku_id + capacity on shelves to track.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-white/60 border-b border-white/10">
                <tr><th className="text-left">SKU</th><th className="text-right">Total</th><th className="text-left pl-2">Shelves</th></tr>
              </thead>
              <tbody>
                {skus.map(k => (
                  <tr key={k.sku_id} className="border-b border-white/5">
                    <td>{k.sku_id}</td>
                    <td className="text-right">{k.total}/{k.capacity}</td>
                    <td className="pl-2 text-white/60 text-xs">{k.shelves.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Middle: new order form + auto-replenish */}
      <div className="col-span-4 space-y-4">
        <div className="border border-white/10 rounded p-3 space-y-2">
          <h3 className="font-bold">New order (manual)</h3>
          <label className="block text-sm">
            <span className="text-white/60">SKU</span>
            <input value={newSku} onChange={e => setNewSku(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1" />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Source shelf</span>
            <select value={newSrc} onChange={e => setNewSrc(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
              {shelves.map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Destination shelf</span>
            <select value={newDst} onChange={e => setNewDst(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
              {shelves.filter(s => s.id !== newSrc).map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Qty</span>
            <input type="number" min={1} value={newQty} onChange={e => setNewQty(parseInt(e.target.value || "1"))} className="w-full bg-black border border-white/20 px-2 py-1" />
          </label>
          <button type="button" onClick={handleCreate} className="w-full px-3 py-2 bg-blue-600 rounded">Queue order</button>
        </div>

        <div className="border border-white/10 rounded p-3 space-y-2">
          <h3 className="font-bold">Auto-replenish</h3>
          <label className="block text-sm">
            <span className="text-white/60">Low-stock threshold: {thresholdPct}%</span>
            <input type="range" min={5} max={95} value={thresholdPct} onChange={e => setThresholdPct(parseInt(e.target.value))} className="w-full" />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={handlePreview} className="flex-1 px-3 py-2 bg-amber-600 rounded">Preview</button>
            <button type="button" onClick={handleRun} className="flex-1 px-3 py-2 bg-green-600 rounded">Run</button>
          </div>
          {proposals && proposals.length > 0 && (
            <div className="text-xs space-y-1 pt-2 border-t border-white/10">
              {proposals.map((p, i) => (
                <div key={i} className="text-white/70">
                  {p.qty}x <strong>{p.sku_id}</strong>: {p.source_shelf_id} → {p.destination_shelf_id}
                </div>
              ))}
            </div>
          )}
        </div>

        {message && <div className="text-sm text-white/80">{message}</div>}
      </div>

      {/* Right: order queue */}
      <div className="col-span-4 space-y-2">
        <h3 className="font-bold">Order queue</h3>
        <div className="text-xs text-white/50">Newest first. Auto-refreshes every 2 s.</div>
        <div className="max-h-[600px] overflow-auto border border-white/10 rounded">
          {orders.length === 0 ? (
            <div className="p-3 text-sm text-white/50">No orders yet.</div>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-white/60 sticky top-0 bg-black border-b border-white/10">
                <tr>
                  <th className="text-left p-1">#</th>
                  <th className="text-left">SKU</th>
                  <th className="text-left">Route</th>
                  <th className="text-right">Qty</th>
                  <th className="text-left">Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id} className="border-b border-white/5">
                    <td className="p-1">{o.id}</td>
                    <td>{o.sku_id}</td>
                    <td className="text-white/70">{o.source_shelf_id}→{o.destination_shelf_id}</td>
                    <td className="text-right">{o.qty}</td>
                    <td>
                      <span className={
                        o.status === "pending" ? "text-amber-400" :
                        o.status === "running" ? "text-blue-400" :
                        o.status === "done" ? "text-green-400" :
                        o.status === "failed" ? "text-red-400" :
                        "text-white/50"
                      }>{o.status}</span>
                    </td>
                    <td>
                      {o.status === "pending" && (
                        <button type="button" onClick={() => handleCancel(o.id)} className="text-red-400 hover:text-red-300 text-xs">cancel</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
