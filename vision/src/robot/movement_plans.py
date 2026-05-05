"""Persistent named movement plans + executor.

A movement plan is an ordered list of low-level steps the operator builds
in the Calibration UI to script a custom robot maneuver — useful for
calibration runs (e.g. "drive forward 1s, lift to 5cm, slider out") that
the canned pick/place flow doesn't cover.

Storage: a single JSON file at vision/state/movement_plans.json shaped as
    { "plans": { <name>: { "steps": [...] } } }

Executor: runs steps sequentially against a WifiLink (real hardware) or
the in-process FakeLink (sim mode). Each step yields a result dict
matching the canned-execute trace shape so the UI can reuse its renderer.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Iterator, Literal, Optional


# --- Step types --------------------------------------------------------------
#
# Adding a step type means:
#   1. add the literal to StepType
#   2. add a clause in execute_step() below
#   3. update the validation in validate_step()

StepType = Literal[
    "drive_forward", "drive_backward", "turn_left", "turn_right",
    "lift_to", "lift_up_for", "lift_down_for",
    "slider_extend", "slider_retract",
    "gripper_open", "gripper_close",
    "wait",
]


@dataclass(frozen=True)
class MovementStep:
    """One step in a movement plan. Field meanings depend on `type`:

      drive_*, turn_*, lift_up_for, lift_down_for, wait -> duration_ms
      lift_to                                            -> target_cm
      slider_*, gripper_*                                -> no params
    """
    type: str
    duration_ms: int = 0
    target_cm: float = 0.0
    note: str = ""


@dataclass(frozen=True)
class MovementPlan:
    name: str
    steps: list[MovementStep] = field(default_factory=list)
    note: str = ""


@dataclass
class StepResult:
    label: str
    ok: bool
    elapsed_ms: int
    reply: str = ""
    error: str | None = None


class MovementPlansError(Exception):
    pass


# --- Validation --------------------------------------------------------------

_STEP_TYPES: set[str] = set(StepType.__args__)  # type: ignore[attr-defined]
_DURATION_TYPES = {
    "drive_forward", "drive_backward", "turn_left", "turn_right",
    "lift_up_for", "lift_down_for", "wait",
}
_TARGET_TYPES = {"lift_to"}


def validate_step(step: MovementStep) -> None:
    if step.type not in _STEP_TYPES:
        raise MovementPlansError(
            f"unknown step type {step.type!r}; expected one of {sorted(_STEP_TYPES)}"
        )
    if step.type in _DURATION_TYPES:
        if step.duration_ms <= 0:
            raise MovementPlansError(
                f"step {step.type!r} requires duration_ms > 0, got {step.duration_ms}"
            )
        # Prevent runaway sleeps. 60s per step is more than any single move
        # should ever need; a calibration sequence chains shorter steps.
        if step.duration_ms > 60_000:
            raise MovementPlansError(
                f"step {step.type!r} duration_ms={step.duration_ms} exceeds 60_000ms cap"
            )
    if step.type in _TARGET_TYPES:
        if step.target_cm <= 0:
            raise MovementPlansError(
                f"step {step.type!r} requires target_cm > 0, got {step.target_cm}"
            )


def validate_plan(plan: MovementPlan) -> None:
    if not plan.name.strip():
        raise MovementPlansError("plan name must be non-empty")
    if "/" in plan.name or "\\" in plan.name:
        raise MovementPlansError("plan name must not contain path separators")
    for i, step in enumerate(plan.steps):
        try:
            validate_step(step)
        except MovementPlansError as e:
            raise MovementPlansError(f"step {i}: {e}") from e


# --- Storage -----------------------------------------------------------------

_io_lock = Lock()


def _read_raw(path: Path) -> dict:
    if not path.exists():
        return {"plans": {}}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "plans" not in data:
        raise MovementPlansError(f"malformed plans file at {path}")
    return data


def _write_raw(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def _step_to_dict(s: MovementStep) -> dict:
    out = {"type": s.type}
    if s.type in _DURATION_TYPES:
        out["duration_ms"] = s.duration_ms
    if s.type in _TARGET_TYPES:
        out["target_cm"] = s.target_cm
    if s.note:
        out["note"] = s.note
    return out


def _step_from_dict(raw: dict) -> MovementStep:
    return MovementStep(
        type=str(raw["type"]),
        duration_ms=int(raw.get("duration_ms", 0)),
        target_cm=float(raw.get("target_cm", 0.0)),
        note=str(raw.get("note", "")),
    )


def list_plans(path: Path) -> list[MovementPlan]:
    with _io_lock:
        data = _read_raw(path)
    plans: list[MovementPlan] = []
    for name, raw in data["plans"].items():
        plans.append(MovementPlan(
            name=str(name),
            steps=[_step_from_dict(s) for s in raw.get("steps", [])],
            note=str(raw.get("note", "")),
        ))
    return sorted(plans, key=lambda p: p.name)


def get_plan(path: Path, name: str) -> MovementPlan:
    for p in list_plans(path):
        if p.name == name:
            return p
    raise MovementPlansError(f"unknown plan {name!r}")


def save_plan(path: Path, plan: MovementPlan) -> None:
    validate_plan(plan)
    with _io_lock:
        data = _read_raw(path)
        data["plans"][plan.name] = {
            "steps": [_step_to_dict(s) for s in plan.steps],
            "note": plan.note,
        }
        _write_raw(path, data)


def delete_plan(path: Path, name: str) -> None:
    with _io_lock:
        data = _read_raw(path)
        if name not in data["plans"]:
            raise MovementPlansError(f"unknown plan {name!r}")
        del data["plans"][name]
        _write_raw(path, data)


# --- Execution ---------------------------------------------------------------
#
# `link` is duck-typed: must expose drive_forward / drive_backward /
# turn_left / turn_right / lift_to / lift_up_for / lift_down_for /
# slider_extend / slider_retract / gripper_open / gripper_close. Both
# WifiLink and FakeWifiLink (tests) satisfy this.

def execute_step(link, step: MovementStep) -> StepResult:
    """Run one step against `link`. Returns StepResult mirroring the
    canned-execute step trace shape so the UI can render uniformly."""
    label = _step_label(step)
    if step.type == "wait":
        time.sleep(step.duration_ms / 1000.0)
        return StepResult(label=label, ok=True, elapsed_ms=step.duration_ms, reply="OK")

    method = _METHOD_DISPATCH.get(step.type)
    if method is None:
        return StepResult(
            label=label, ok=False, elapsed_ms=0,
            error=f"no dispatcher for step type {step.type!r}",
        )
    fn = getattr(link, method, None)
    if fn is None:
        return StepResult(
            label=label, ok=False, elapsed_ms=0,
            error=f"link has no method {method!r}",
        )

    args = _step_args(step)
    ack = fn(*args)
    return StepResult(
        label=label,
        ok=bool(ack.ok),
        elapsed_ms=int(ack.elapsed_ms),
        reply=str(ack.reply or ""),
        error=ack.error,
    )


def execute_plan(link, plan: MovementPlan) -> Iterator[StepResult]:
    """Yield StepResult per step. Stops on first failure (caller may keep
    consuming; remaining steps simply aren't executed)."""
    validate_plan(plan)
    for step in plan.steps:
        result = execute_step(link, step)
        yield result
        if not result.ok:
            return


# --- Step-type dispatch helpers ---------------------------------------------

_METHOD_DISPATCH: dict[str, str] = {
    "drive_forward": "drive_forward",
    "drive_backward": "drive_backward",
    "turn_left": "turn_left",
    "turn_right": "turn_right",
    "lift_to": "lift_to",
    "lift_up_for": "lift_up_for",
    "lift_down_for": "lift_down_for",
    "slider_extend": "slider_extend",
    "slider_retract": "slider_retract",
    "gripper_open": "gripper_open",
    "gripper_close": "gripper_close",
}


def _step_args(step: MovementStep) -> tuple:
    if step.type in _DURATION_TYPES:
        return (step.duration_ms,)
    if step.type in _TARGET_TYPES:
        return (step.target_cm,)
    return ()


def _step_label(step: MovementStep) -> str:
    if step.type in _DURATION_TYPES:
        return f"{step.type}({step.duration_ms}ms)"
    if step.type in _TARGET_TYPES:
        return f"{step.type}({step.target_cm:.1f}cm)"
    return step.type


# --- Sim-mode fake link -----------------------------------------------------
#
# WifiLink methods all return SubAck. Sim mode for plans needs the same
# duck-typed surface without doing any HTTP. Sleeps mirror the wall-clock
# durations so the operator gets a realistic preview before running on
# real hardware.

class _FakeAck:
    """Minimal SubAck shape duck-compatible with execute_step()."""
    def __init__(self, reply: str = "OK", elapsed_ms: int = 0,
                 ok: bool = True, error: Optional[str] = None):
        self.reply = reply
        self.elapsed_ms = elapsed_ms
        self.ok = ok
        self.error = error


class FakeMovementLink:
    """In-process fake exposing the same methods as WifiLink that the plan
    executor calls. Sleeps for realism, returns OK acks."""
    def __init__(self, time_scale: float = 1.0):
        self.time_scale = time_scale

    def _sleep_ms(self, ms: int) -> _FakeAck:
        time.sleep((ms / 1000.0) * self.time_scale)
        return _FakeAck(reply="OK", elapsed_ms=ms)

    def drive_forward(self, ms: int) -> _FakeAck: return self._sleep_ms(ms)
    def drive_backward(self, ms: int) -> _FakeAck: return self._sleep_ms(ms)
    def turn_left(self, ms: int) -> _FakeAck: return self._sleep_ms(ms)
    def turn_right(self, ms: int) -> _FakeAck: return self._sleep_ms(ms)
    def lift_up_for(self, ms: int) -> _FakeAck: return self._sleep_ms(ms)
    def lift_down_for(self, ms: int) -> _FakeAck: return self._sleep_ms(ms)

    def lift_to(self, target_cm: float) -> _FakeAck:
        # Pretend it took 2s to drive to the target.
        return self._sleep_ms(2000)

    def slider_extend(self) -> _FakeAck: return self._sleep_ms(500)
    def slider_retract(self) -> _FakeAck: return self._sleep_ms(500)
    def gripper_open(self) -> _FakeAck: return self._sleep_ms(200)
    def gripper_close(self) -> _FakeAck: return self._sleep_ms(200)
