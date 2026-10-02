from dataclasses import replace
from random import Random

from pallet_building_packer import (
    Carton,
    PackRequest,
    Pallet,
    make_instructions,
    pack,
    validate_instruction_sequence,
    validate_result,
)


def assert_grid_oracle(request: PackRequest, result) -> None:
    """Independent 100 mm cell oracle for this synthetic test corpus."""
    requested = {item.instance_id for item in request.cartons}
    assert requested == {item.instance_id for item in result.placed} | {item.instance_id for item in result.unplaced}
    assert len(result.placed) + len(result.unplaced) == len(requested)
    occupied: set[tuple[int, int, int, int]] = set()
    pallet_masses = [0] * request.pallet.available_count
    for item in result.placed:
        assert min(item.x_mm, item.y_mm, item.z_mm) >= 0
        assert item.x_mm + item.length_mm <= request.pallet.length_mm
        assert item.y_mm + item.width_mm <= request.pallet.width_mm
        assert request.pallet.deck_height_mm + item.z_mm + item.height_mm <= request.pallet.max_total_height_mm
        assert all(value % 100 == 0 for value in (item.x_mm, item.y_mm, item.z_mm, item.length_mm, item.width_mm, item.height_mm))
        pallet_masses[item.pallet_index] += item.mass_g
        for x in range(item.x_mm, item.x_mm + item.length_mm, 100):
            for y in range(item.y_mm, item.y_mm + item.width_mm, 100):
                for z in range(item.z_mm, item.z_mm + item.height_mm, 100):
                    cell = (item.pallet_index, x, y, z)
                    assert cell not in occupied
                    occupied.add(cell)
    assert all(mass <= request.pallet.max_cargo_mass_g for mass in pallet_masses)
    for item in result.placed:
        if item.z_mm:
            for x in range(item.x_mm, item.x_mm + item.length_mm, 100):
                for y in range(item.y_mm, item.y_mm + item.width_mm, 100):
                    assert (item.pallet_index, x, y, item.z_mm - 100) in occupied


def fixture(count: int = 16) -> PackRequest:
    pallet = Pallet(1200, 800, 144, 544, 100_000, 1)
    cartons = tuple(Carton(str(i), "A", 400, 300, 200, 5000, 10_000, ("upright_0", "upright_90")) for i in range(count))
    return PackRequest(cartons, pallet)


def test_reference_16_cartons() -> None:
    request = fixture()
    result = pack(request)
    assert len(result.placed) == 16
    assert not result.unplaced
    assert max(item.z_mm + item.height_mm for item in result.placed) == 400
    assert all(item.orientation_code == "upright_90" for item in result.placed)
    assert validate_result(request, result) == ()


def test_unknown_load_blocks_stacking_without_losing_instances() -> None:
    original = fixture(20)
    request = replace(original, cartons=tuple(replace(c, top_load_limit_g=None) for c in original.cartons))
    result = pack(request)
    assert len(result.placed) == 8
    assert len(result.unplaced) == 12
    assert validate_result(request, result) == ()


def test_validator_rejects_levitation_and_overlap() -> None:
    request = fixture(2)
    result = pack(request)
    levitating = replace(result, placed=(replace(result.placed[0], z_mm=100), result.placed[1]))
    assert "UNSUPPORTED_STACK" in validate_result(request, levitating)
    overlapping = replace(result, placed=(result.placed[0], replace(result.placed[1], x_mm=0, y_mm=0)))
    assert "COLLISION" in validate_result(request, overlapping)


def test_manifest_keeps_every_instance() -> None:
    request = fixture(100)
    result = pack(request)
    assert len(result.placed) + len(result.unplaced) == 100
    assert validate_result(request, result) == ()


def test_mixed_cartons_share_deck_without_overlap() -> None:
    request = PackRequest((
        Carton("a", "A", 600, 400, 200, 8000, None),
        Carton("b", "B", 300, 400, 100, 3000, None),
        Carton("c", "B", 300, 400, 100, 3000, None),
    ), Pallet(1200, 800, 144, 700, 100_000, 1))
    result = pack(request)
    assert len(result.placed) == 3
    assert {item.sku for item in result.placed} == {"A", "B"}
    assert all(item.z_mm == 0 for item in result.placed)
    assert validate_result(request, result) == ()


def test_mixed_exact_column_respects_unknown_top_load() -> None:
    request = PackRequest((
        Carton("large", "A", 400, 400, 200, 5000, None),
        Carton("small", "B", 400, 400, 100, 2000, 0),
    ), Pallet(400, 400, 144, 500, 20_000, 1))
    result = pack(request)
    assert len(result.placed) == 1
    assert len(result.unplaced) == 1
    assert result.unplaced[0].sku == "B"
    assert validate_result(request, result) == ()


def test_mixed_exact_column_allows_known_load() -> None:
    request = PackRequest((
        Carton("large", "A", 400, 400, 200, 5000, 4000),
        Carton("small", "B", 400, 400, 100, 2000, 0),
    ), Pallet(400, 400, 144, 500, 20_000, 1))
    result = pack(request)
    assert len(result.placed) == 2
    assert sorted(item.z_mm for item in result.placed) == [0, 200]
    assert validate_result(request, result) == ()


def test_best_fit_improves_a_mixed_footprint_without_losing_quick_baseline() -> None:
    request = PackRequest((
        Carton("a", "A", 300, 300, 100, 1000, None, ("upright_0", "upright_90")),
        Carton("b", "B", 100, 300, 100, 1000, None, ("upright_0", "upright_90")),
        Carton("c", "C", 400, 300, 100, 1000, None, ("upright_0", "upright_90")),
    ), Pallet(600, 400, 100, 600, 50_000, 1))
    quick = pack(request)
    improved = pack(replace(request, strategy="best_fit"))
    assert len(quick.placed) == 2
    assert len(improved.placed) == 3
    assert improved.candidates_completed > 1
    assert validate_result(request, improved) == ()
    assert pack(replace(request, strategy="best_fit")) == improved
    budgeted = pack(replace(request, strategy="best_fit", evaluation_budget=1))
    assert budgeted.termination_reason == "evaluation_budget_exhausted"
    assert len(budgeted.placed) == len(quick.placed)
    assert validate_result(request, budgeted) == ()


def test_instruction_prefix_rejects_top_before_its_support() -> None:
    request = fixture()
    result = pack(request)
    correct = make_instructions(result)
    assert validate_instruction_sequence(request, result, correct) == ()
    top_id = next(item.instance_id for item in result.placed if item.z_mm > 0)
    wrong_order = [next(step for step in correct if step["instance_id"] == top_id)] + [step for step in correct if step["instance_id"] != top_id]
    wrong_steps = [{**step, "sequence_no": index} for index, step in enumerate(wrong_order, 1)]
    assert "INSTRUCTION_SUPPORT_NOT_READY" in validate_instruction_sequence(request, result, wrong_steps)


def test_br2_synthetic_mixed_cartons_need_only_two_pallets() -> None:
    """Regression for the BR2 dimensions; no production data is read by tests."""
    groups = (
        ("PARTS", 3, 600, 400, 220, 18_000, 36_000, True),
        ("LAMP", 3, 500, 400, 350, 7_000, 0, False),
        ("GLASS", 4, 300, 200, 250, 8_000, 0, False),
        ("BOOK", 3, 300, 200, 200, 10_000, 20_000, True),
        ("CLOTH", 3, 400, 300, 180, 4_000, 16_000, True),
        ("TALL", 2, 400, 300, 600, 5_000, 50_000, False),
        ("BOX", 3, 400, 300, 200, 5_000, 500_000, True),
    )
    cartons = tuple(
        Carton(f"{sku}-{index}", sku, length, width, height, mass, top_load,
               ("upright_0", "upright_90") if rotate else ("upright_0",))
        for sku, count, length, width, height, mass, top_load, rotate in groups
        for index in range(count)
    )
    request = PackRequest(cartons, Pallet(1200, 800, 150, 1250, 300_000, 3), strategy="best_fit")
    for strategy in ("quick", "best_fit"):
        variant = replace(request, strategy=strategy)
        result = pack(variant)
        assert len(result.placed) == 21
        assert result.unplaced == ()
        assert len({item.pallet_index for item in result.placed}) == 2
        assert any(item.z_mm > 0 for item in result.placed)
        assert validate_result(variant, result) == ()
        assert validate_instruction_sequence(variant, result, make_instructions(result)) == ()


def test_generated_mixed_requests_conserve_and_validate_every_instance() -> None:
    random = Random(20261002)
    pallet = Pallet(600, 400, 100, 600, 30_000, 2)
    for _ in range(100):
        cartons = tuple(Carton(str(index), f"SKU-{index % 3}", random.choice((100, 200, 300, 400)), random.choice((100, 200, 300)), random.choice((100, 200)), random.choice((1000, 2000, 3000)), random.choice((None, 0, 3000, 6000)), ("upright_0", "upright_90")) for index in range(random.randint(1, 15)))
        request = PackRequest(cartons, pallet)
        quick = pack(request)
        best = pack(replace(request, strategy="best_fit", evaluation_budget=20_000))
        for result in (quick, best):
            assert len(result.placed) + len(result.unplaced) == len(cartons)
            assert validate_result(request, result) == ()
            assert validate_instruction_sequence(request, result, make_instructions(result)) == ()
            assert_grid_oracle(request, result)
        assert len(best.unplaced) <= len(quick.unplaced)
        if len(best.unplaced) == len(quick.unplaced):
            assert len({item.pallet_index for item in best.placed}) <= len({item.pallet_index for item in quick.placed})
