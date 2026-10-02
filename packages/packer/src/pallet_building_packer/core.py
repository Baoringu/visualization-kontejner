"""Conservative, deterministic column palletizer. No database or web imports."""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from typing import Literal

Orientation = Literal["upright_0", "upright_90"]
Strategy = Literal["quick", "best_fit"]


@dataclass(frozen=True)
class Carton:
    instance_id: str
    sku: str
    length_mm: int
    width_mm: int
    height_mm: int
    mass_g: int
    top_load_limit_g: int | None
    allowed_orientations: tuple[Orientation, ...] = ("upright_0",)


@dataclass(frozen=True)
class Pallet:
    length_mm: int
    width_mm: int
    deck_height_mm: int
    max_total_height_mm: int
    max_cargo_mass_g: int
    available_count: int
    support_model: Literal["solid_deck"] = "solid_deck"


@dataclass(frozen=True)
class PackRequest:
    cartons: tuple[Carton, ...]
    pallet: Pallet
    strategy: Strategy = "quick"
    evaluation_budget: int = 250_000


@dataclass(frozen=True)
class Placement:
    instance_id: str
    pallet_index: int
    x_mm: int
    y_mm: int
    z_mm: int
    orientation_code: Orientation
    length_mm: int
    width_mm: int
    height_mm: int
    sku: str = ""
    mass_g: int = 0


@dataclass(frozen=True)
class Unplaced:
    instance_id: str
    reason: str
    sku: str = ""


@dataclass(frozen=True)
class PackResult:
    placed: tuple[Placement, ...]
    unplaced: tuple[Unplaced, ...]
    termination_reason: str
    evaluations_completed: int
    candidates_completed: int = 1


def _size(carton: Carton, orientation: Orientation) -> tuple[int, int, int]:
    if orientation == "upright_90":
        return carton.width_mm, carton.length_mm, carton.height_mm
    return carton.length_mm, carton.width_mm, carton.height_mm


def _require_positive(request: PackRequest) -> None:
    p = request.pallet
    if any(v <= 0 for v in (p.length_mm, p.width_mm, p.deck_height_mm, p.max_total_height_mm, p.max_cargo_mass_g, p.available_count)):
        raise ValueError("INVALID_PALLET")
    if p.support_model != "solid_deck":
        raise ValueError("UNSUPPORTED_DECK_MODEL")
    if request.strategy not in ("quick", "best_fit") or request.evaluation_budget <= 0:
        raise ValueError("INVALID_SEARCH_OPTIONS")
    ids: set[str] = set()
    for c in request.cartons:
        if c.instance_id in ids:
            raise ValueError("DUPLICATE_INSTANCE_ID")
        ids.add(c.instance_id)
        if any(v <= 0 for v in (c.length_mm, c.width_mm, c.height_mm, c.mass_g)):
            raise ValueError("INVALID_CARTON")
        if not c.allowed_orientations or any(o not in ("upright_0", "upright_90") for o in c.allowed_orientations):
            raise ValueError("UNSUPPORTED_ORIENTATION")
        if c.top_load_limit_g is not None and c.top_load_limit_g < 0:
            raise ValueError("INVALID_TOP_LOAD_LIMIT")


def pack(request: PackRequest) -> PackResult:
    """Compare bounded candidates while retaining the validated Quick baseline."""
    _require_positive(request)
    baseline = _pack_quick(request)
    if request.strategy == "quick" or not request.cartons:
        return baseline
    if validate_result(request, baseline):
        raise ValueError("INVALID_QUICK_BASELINE")
    best = baseline
    evaluations = baseline.evaluations_completed
    candidates = 1
    remaining = request.evaluation_budget
    exhausted = False
    for order, reverse_orientation, point_axis, stack_first in (
        ("area", True, "x", False),
        ("area", False, "y", True),
        ("mass", False, "x", True),
        ("height", True, "y", True),
        ("short_side", False, "y", False),
        ("fragile_first", False, "x", True),
    ):
        try:
            candidate = _pack_mixed(request, order=order, reverse_orientation=reverse_orientation, point_axis=point_axis, stack_first=stack_first, evaluation_limit=remaining)
        except _SearchBudgetReached as error:
            evaluations += error.evaluations
            exhausted = True
            break
        evaluations += candidate.evaluations_completed
        remaining -= candidate.evaluations_completed
        candidates += 1
        if not validate_result(request, candidate) and _score(candidate, request.pallet) < _score(best, request.pallet):
            best = candidate
        if remaining == 0:
            exhausted = True
            break
    return replace(best, termination_reason="evaluation_budget_exhausted" if exhausted else "search_completed", evaluations_completed=evaluations, candidates_completed=candidates)


def _pack_quick(request: PackRequest) -> PackResult:
    cartons = request.cartons
    if not cartons:
        return PackResult((), (), "search_completed", 0)
    first = cartons[0]
    signature = (first.sku, first.length_mm, first.width_mm, first.height_mm, first.mass_g, first.top_load_limit_g, first.allowed_orientations)
    if any((c.sku, c.length_mm, c.width_mm, c.height_mm, c.mass_g, c.top_load_limit_g, c.allowed_orientations) != signature for c in cartons):
        return _pack_mixed(request)
    p = request.pallet
    options: list[tuple[int, Orientation, int, int]] = []
    for orientation in first.allowed_orientations:
        length, width, _ = _size(first, orientation)
        capacity = (p.length_mm // length) * (p.width_mm // width)
        options.append((capacity, orientation, length, width))
    capacity, orientation, length, width = max(options, key=lambda value: (value[0], value[1] == "upright_0"))
    if capacity == 0 or p.deck_height_mm + first.height_mm > p.max_total_height_mm or first.mass_g > p.max_cargo_mass_g:
        return PackResult((), tuple(Unplaced(c.instance_id, "NO_FEASIBLE_PLACEMENT", c.sku) for c in cartons), "search_completed", len(options))
    columns = [(x * length, y * width) for y in range(p.width_mm // width) for x in range(p.length_mm // length)]
    max_levels_by_height = (p.max_total_height_mm - p.deck_height_mm) // first.height_mm
    max_levels_by_top = 1 if first.top_load_limit_g is None else 1 + first.top_load_limit_g // first.mass_g
    max_levels = min(max_levels_by_height, max_levels_by_top)
    placements: list[Placement] = []
    unplaced: list[Unplaced] = []
    pallet_masses = [0] * p.available_count
    for carton in cartons:
        candidate = None
        for pallet_index in range(p.available_count):
            if pallet_masses[pallet_index] + carton.mass_g > p.max_cargo_mass_g:
                continue
            count = sum(placement.pallet_index == pallet_index for placement in placements)
            if count >= len(columns) * max_levels:
                continue
            level, slot = divmod(count, len(columns))
            candidate = (pallet_index, level, slot)
            break
        if candidate is None:
            unplaced.append(Unplaced(carton.instance_id, "PALLET_CAPACITY_EXHAUSTED", carton.sku))
            continue
        pallet_index, level, slot = candidate
        x, y = columns[slot]
        placements.append(Placement(carton.instance_id, pallet_index, x, y, level * first.height_mm, orientation, length, width, first.height_mm, carton.sku, carton.mass_g))
        pallet_masses[pallet_index] += carton.mass_g
    return PackResult(tuple(placements), tuple(unplaced), "search_completed", len(options))


class _SearchBudgetReached(Exception):
    def __init__(self, evaluations: int):
        self.evaluations = evaluations


def _score(result: PackResult, pallet: Pallet) -> tuple[int, int, int, int, int]:
    """Efficiency profile: completeness, pallet count, heights, then handling."""
    heights: dict[int, int] = {}
    for item in result.placed:
        heights[item.pallet_index] = max(heights.get(item.pallet_index, 0), item.z_mm + item.height_mm + pallet.deck_height_mm)
    ordered = sorted(result.placed, key=lambda item: (item.pallet_index, item.z_mm, item.y_mm, item.x_mm, item.instance_id))
    switches = sum(a.sku != b.sku for a, b in pairwise(ordered))
    return len(result.unplaced), len(heights), max(heights.values(), default=0), sum(heights.values()), switches


def _candidate_placements(kind: str, carton: Carton, pallet_index: int, positions: Sequence[tuple[int, int]], same_pallet: Sequence[Placement], orientations: Sequence[Orientation]) -> Iterator[Placement]:
    if kind == "deck":
        for x, y in positions:
            for orientation in orientations:
                length, width, height = _size(carton, orientation)
                yield Placement(carton.instance_id, pallet_index, x, y, 0, orientation, length, width, height, carton.sku, carton.mass_g)
    else:
        for support in sorted(same_pallet, key=lambda item: (item.z_mm + item.height_mm, item.y_mm, item.x_mm)):
            for orientation in orientations:
                length, width, height = _size(carton, orientation)
                yield Placement(carton.instance_id, pallet_index, support.x_mm, support.y_mm, support.z_mm + support.height_mm, orientation, length, width, height, carton.sku, carton.mass_g)


def _pack_mixed(request: PackRequest, *, order: str = "area", reverse_orientation: bool = False, point_axis: str = "y", stack_first: bool = True, evaluation_limit: int | None = None) -> PackResult:
    """Bottom-left deck placement plus exact-footprint single-support columns.

    Larger cartons are considered first. This is a bounded heuristic, not an
    optimality or physical transport-stability claim.
    """
    p = request.pallet
    sort_keys = {
        "area": lambda c: (-c.length_mm * c.width_mm, -c.mass_g, -c.height_mm, c.sku, c.instance_id),
        "mass": lambda c: (-c.mass_g, -c.length_mm * c.width_mm, -c.height_mm, c.sku, c.instance_id),
        "height": lambda c: (-c.height_mm, -c.length_mm * c.width_mm, -c.mass_g, c.sku, c.instance_id),
        "short_side": lambda c: (-min(c.length_mm, c.width_mm), -c.length_mm * c.width_mm, -c.mass_g, c.sku, c.instance_id),
        "fragile_first": lambda c: (c.top_load_limit_g is not None and c.top_load_limit_g > 0, -c.length_mm * c.width_mm, -c.height_mm, c.sku, c.instance_id),
    }
    ordered = sorted(request.cartons, key=sort_keys[order])
    by_id = {carton.instance_id: carton for carton in request.cartons}
    placed: list[Placement] = []
    unplaced: list[Unplaced] = []
    masses = [0] * p.available_count
    evaluations = 0
    for carton in ordered:
        chosen: Placement | None = None
        for pallet_index in range(p.available_count):
            if masses[pallet_index] + carton.mass_g > p.max_cargo_mass_g:
                continue
            same_pallet = [item for item in placed if item.pallet_index == pallet_index]
            point_key = (lambda point: (point[0], point[1])) if point_axis == "x" else (lambda point: (point[1], point[0]))
            orientations = carton.allowed_orientations[::-1] if reverse_orientation else carton.allowed_orientations
            floor = [item for item in same_pallet if item.z_mm == 0]
            x_edges = {0} | {item.x_mm + item.length_mm for item in floor}
            y_edges = {0} | {item.y_mm + item.width_mm for item in floor}
            positions = sorted(((x, y) for x in x_edges for y in y_edges if x < p.length_mm and y < p.width_mm), key=point_key)
            for kind in (("column", "deck") if stack_first else ("deck", "column")):
                for candidate in _candidate_placements(kind, carton, pallet_index, positions, same_pallet, orientations):
                    if evaluation_limit is not None and evaluations >= evaluation_limit:
                        raise _SearchBudgetReached(evaluations)
                    evaluations += 1
                    if candidate.x_mm + candidate.length_mm > p.length_mm or candidate.y_mm + candidate.width_mm > p.width_mm or p.deck_height_mm + candidate.z_mm + candidate.height_mm > p.max_total_height_mm:
                        continue
                    if kind == "column":
                        support = next((item for item in same_pallet if item.x_mm == candidate.x_mm and item.y_mm == candidate.y_mm and item.z_mm + item.height_mm == candidate.z_mm), None)
                        if support is None or (candidate.length_mm, candidate.width_mm) != (support.length_mm, support.width_mm):
                            continue
                        lower_column = [item for item in same_pallet if item.x_mm == candidate.x_mm and item.y_mm == candidate.y_mm and item.length_mm == candidate.length_mm and item.width_mm == candidate.width_mm and item.z_mm < candidate.z_mm]
                        if any(
                            limit is None or sum(upper.mass_g for upper in lower_column if upper.z_mm > lower.z_mm) + carton.mass_g > limit
                            for lower in lower_column
                            for limit in (by_id[lower.instance_id].top_load_limit_g,)
                        ):
                            continue
                    if any(_overlap(candidate, other) for other in same_pallet):
                        continue
                    chosen = candidate
                    break
                if chosen:
                    break
            if chosen:
                break
        if chosen is None:
            unplaced.append(Unplaced(carton.instance_id, "PALLET_CAPACITY_EXHAUSTED", carton.sku))
            continue
        placed.append(chosen)
        masses[chosen.pallet_index] += carton.mass_g
    return PackResult(tuple(placed), tuple(unplaced), "search_completed", evaluations)


def _overlap(a: Placement, b: Placement) -> bool:
    return (a.x_mm < b.x_mm + b.length_mm and b.x_mm < a.x_mm + a.length_mm
            and a.y_mm < b.y_mm + b.width_mm and b.y_mm < a.y_mm + a.width_mm
            and a.z_mm < b.z_mm + b.height_mm and b.z_mm < a.z_mm + a.height_mm)


def validate_result(request: PackRequest, result: PackResult) -> tuple[str, ...]:
    """Validate geometry, exact single-support columns, loads and manifest independently."""
    issues: list[str] = []
    by_id = {c.instance_id: c for c in request.cartons}
    all_ids = [p.instance_id for p in result.placed] + [u.instance_id for u in result.unplaced]
    if len(all_ids) != len(by_id) or set(all_ids) != set(by_id):
        issues.append("MANIFEST_MISMATCH")
    p = request.pallet
    masses = [0] * p.available_count
    for placed in result.placed:
        carton = by_id.get(placed.instance_id)
        if carton is None:
            issues.append("UNKNOWN_INSTANCE")
            continue
        if placed.pallet_index < 0 or placed.pallet_index >= p.available_count:
            issues.append("PALLET_INDEX_OUT_OF_RANGE")
            continue
        if placed.orientation_code not in carton.allowed_orientations or _size(carton, placed.orientation_code) != (placed.length_mm, placed.width_mm, placed.height_mm):
            issues.append("INVALID_ORIENTATION")
        if placed.sku != carton.sku or placed.mass_g != carton.mass_g:
            issues.append("PLACEMENT_METADATA_MISMATCH")
        if min(placed.x_mm, placed.y_mm, placed.z_mm) < 0 or placed.x_mm + placed.length_mm > p.length_mm or placed.y_mm + placed.width_mm > p.width_mm or p.deck_height_mm + placed.z_mm + placed.height_mm > p.max_total_height_mm:
            issues.append("OUT_OF_BOUNDS")
        masses[placed.pallet_index] += carton.mass_g
    if any(mass > p.max_cargo_mass_g for mass in masses):
        issues.append("PALLET_OVERWEIGHT")
    for missing in result.unplaced:
        carton = by_id.get(missing.instance_id)
        if carton and missing.sku != carton.sku:
            issues.append("UNPLACED_METADATA_MISMATCH")
    for i, item in enumerate(result.placed):
        if any(_overlap(item, other) for other in result.placed[i + 1:] if other.pallet_index == item.pallet_index):
            issues.append("COLLISION")
        if item.z_mm == 0:
            continue
        supports = [other for other in result.placed if other.pallet_index == item.pallet_index and other.z_mm + other.height_mm == item.z_mm and other.x_mm == item.x_mm and other.y_mm == item.y_mm and other.length_mm == item.length_mm and other.width_mm == item.width_mm]
        if len(supports) != 1:
            issues.append("UNSUPPORTED_STACK")
    for lower in result.placed:
        carton = by_id.get(lower.instance_id)
        if carton is None:
            continue
        above_mass = sum(by_id[upper.instance_id].mass_g for upper in result.placed if upper.instance_id in by_id and upper.pallet_index == lower.pallet_index and upper.x_mm == lower.x_mm and upper.y_mm == lower.y_mm and upper.length_mm == lower.length_mm and upper.width_mm == lower.width_mm and upper.z_mm >= lower.z_mm + lower.height_mm)
        if above_mass and (carton.top_load_limit_g is None or above_mass > carton.top_load_limit_g):
            issues.append("TOP_LOAD_EXCEEDED")
    return tuple(sorted(set(issues)))


def make_instructions(result: PackResult) -> tuple[dict[str, int | str], ...]:
    """Every prefix is supported in the column model because levels are ordered bottom-up."""
    ordered = sorted(result.placed, key=lambda item: (item.pallet_index, item.z_mm, item.y_mm, item.x_mm, item.instance_id))
    return tuple({"sequence_no": index, "instance_id": item.instance_id, "pallet_index": item.pallet_index} for index, item in enumerate(ordered, 1))


def validate_instruction_sequence(request: PackRequest, result: PackResult, steps: Sequence[Mapping[str, int | str]]) -> tuple[str, ...]:
    """Check that each exact-column support exists before its dependent step."""
    findings = list(validate_result(request, result))
    by_id = {item.instance_id: item for item in result.placed}
    if len(steps) != len(by_id):
        findings.append("INSTRUCTION_MANIFEST_MISMATCH")
    seen: set[str] = set()
    for expected, step in enumerate(steps, 1):
        identifier = step.get("instance_id")
        if not isinstance(identifier, str) or identifier in seen or identifier not in by_id:
            findings.append("INSTRUCTION_MANIFEST_MISMATCH")
            continue
        item = by_id[identifier]
        if step.get("sequence_no") != expected or step.get("pallet_index") != item.pallet_index:
            findings.append("INSTRUCTION_METADATA_MISMATCH")
        if item.z_mm > 0:
            supports = [lower for lower in result.placed if lower.pallet_index == item.pallet_index and lower.x_mm == item.x_mm and lower.y_mm == item.y_mm and lower.length_mm == item.length_mm and lower.width_mm == item.width_mm and lower.z_mm + lower.height_mm == item.z_mm]
            if len(supports) != 1 or supports[0].instance_id not in seen:
                findings.append("INSTRUCTION_SUPPORT_NOT_READY")
        seen.add(identifier)
    if seen != set(by_id):
        findings.append("INSTRUCTION_MANIFEST_MISMATCH")
    return tuple(sorted(set(findings)))
