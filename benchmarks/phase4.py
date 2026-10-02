"""Repeatable in-process Quick/Best-fit corpus; does not touch databases."""

import json
import os
import platform
import random
import resource
import statistics
import time
from dataclasses import replace

from pallet_building_packer import (
    Carton,
    PackRequest,
    Pallet,
    make_instructions,
    pack,
    validate_instruction_sequence,
    validate_result,
)

SEED = 20261002
REPEATS = 5


def corpus() -> dict[str, PackRequest]:
    rng = random.Random(SEED)
    standard = Pallet(1200, 800, 144, 1244, 800_000, 10)
    tight = Pallet(1200, 800, 144, 744, 150_000, 3)
    return {
        "uniform_500": PackRequest(tuple(Carton(str(i), "A", 400, 300, 200, 5000, 10_000, ("upright_0", "upright_90")) for i in range(500)), standard),
        "mixed_500": PackRequest(tuple(Carton(str(i), f"SKU-{i % 5}", rng.choice((200, 300, 400)), rng.choice((200, 300)), rng.choice((100, 200)), rng.choice((1000, 2000, 3000)), rng.choice((None, 3000, 6000)), ("upright_0", "upright_90")) for i in range(500)), standard),
        "heavy_fragile_150": PackRequest(tuple(Carton(str(i), f"SKU-{i % 4}", rng.choice((300, 400, 500)), rng.choice((200, 300)), 200, rng.choice((5000, 7000, 9000)), None if i % 3 else 0) for i in range(150)), standard),
        "near_capacity_200": PackRequest(tuple(Carton(str(i), f"SKU-{i % 3}", rng.choice((300, 400, 600)), rng.choice((200, 400)), 200, rng.choice((2000, 4000, 6000)), 6000, ("upright_0", "upright_90")) for i in range(200)), tight),
        "infeasible_80": PackRequest(tuple(Carton(str(i), "TOO-WIDE", 1300, 900, 200, 1000, None) for i in range(80)), standard),
        "orientations_250": PackRequest(tuple(Carton(str(i), f"SKU-{i % 2}", 400, 300, 100, 2000, 4000, ("upright_0", "upright_90")) for i in range(250)), standard),
    }


def run() -> None:
    report: dict = {
        "seed": SEED,
        "repeats": REPEATS,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "cases": {},
    }
    for name, request in corpus().items():
        variants = {}
        for strategy in ("quick", "best_fit"):
            durations = []
            result = None
            for _ in range(REPEATS):
                started = time.perf_counter()
                result = pack(replace(request, strategy=strategy))
                durations.append((time.perf_counter() - started) * 1000)
                findings = validate_result(request, result) + validate_instruction_sequence(request, result, make_instructions(result))
                if findings:
                    raise AssertionError(f"{name}/{strategy}: {findings}")
            assert result is not None
            variants[strategy] = {
                "p50_ms": round(statistics.median(durations), 2),
                "p95_ms": round(statistics.quantiles(durations, n=20, method="inclusive")[-1], 2),
                "placed": len(result.placed),
                "unplaced": len(result.unplaced),
                "pallets": len({item.pallet_index for item in result.placed}),
                "evaluations": result.evaluations_completed,
                "candidates": result.candidates_completed,
                "termination": result.termination_reason,
            }
        if variants["best_fit"]["unplaced"] > variants["quick"]["unplaced"]:
            raise AssertionError(f"{name}: Best fit lost cartons")
        report["cases"][name] = {"requested": len(request.cartons), **variants}
    report["peak_rss_raw"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report["peak_rss_unit"] = "bytes" if platform.system() == "Darwin" else "KiB"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
