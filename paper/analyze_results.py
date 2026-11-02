#!/usr/bin/env python3
"""Audit COUNTERFORM's saved evidence without fitting or simulating anything.

Usage: python paper/analyze_results.py [--root PATH] [--output PATH]

Only the output directory is written. All calculations use the Python standard
library and saved receipts. No engine code is imported or executed. Integrity
checks are checksums, not authentication, and do not establish solver accuracy.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import platform
import statistics
import zipfile


STRATEGIES = ("passive", "random", "active", "counterform")
PHYSICAL_KEYS = ("mass", "stiffness", "damping", "tuning_ratio", "mass_ratio", "damping_ratio")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def rms(values):
    values = list(values)
    return math.sqrt(math.fsum(value * value for value in values) / len(values))


def mean(values):
    return statistics.fmean(values)


def reduction(baseline, design):
    return 100 * (1 - design / baseline)


def close(actual, expected, label, errors, tolerance=1e-12):
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        errors.append({"check": label, "actual": actual, "expected": expected})


def require(condition, label, errors):
    if not condition:
        errors.append({"check": label})


def verify_receipt(receipt, label, errors):
    require(receipt.get("schema") == "counterform.receipt.v1", label + ": receipt schema", errors)
    payload = {key: value for key, value in receipt.items() if key != "payload_sha256"}
    require(sha256(canonical(payload)) == receipt["payload_sha256"], label + ": payload hash", errors)
    require(sha256(canonical(receipt["result"])) == receipt["result_sha256"], label + ": result hash", errors)
    require(receipt["config"] == receipt["result"]["config"], label + ": config agreement", errors)


def verify_archive(directory, receipt, root, errors):
    label = directory.relative_to(root).as_posix()
    path = directory / "evidence.zip"
    external_receipt = (directory / "receipt.json").read_bytes()
    external_report = (directory / "report.html").read_bytes()
    before = len(errors)
    verify_receipt(receipt, label, errors)
    expected = {"receipt.json", "design.json", "design.stl", "report.html", "README.txt"}
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), label + ": no duplicate zip entries", errors)
        require(set(names) == expected | {"manifest.json"}, label + ": zip entry set", errors)
        require(len(names) <= 32 and sum(i.file_size for i in archive.infolist()) <= 30_000_000,
                label + ": zip size bounds", errors)
        for name in names:
            parsed = PurePosixPath(name)
            require(not parsed.is_absolute() and len(parsed.parts) == 1 and ".." not in parsed.parts
                    and "\\" not in name and ":" not in name, label + ": safe zip path " + name, errors)
        manifest = json.loads(archive.read("manifest.json"))
        require(manifest["schema"] == "counterform.bundle.v1", label + ": manifest schema", errors)
        require(set(manifest["files"]) == expected, label + ": manifest file set", errors)
        for name, digest in manifest["files"].items():
            require(sha256(archive.read(name)) == digest, label + ": member checksum " + name, errors)
        require(archive.read("receipt.json") == external_receipt,
                label + ": external/embedded receipt bytes", errors)
        embedded_report = archive.read("report.html")
        report_bytes_equal = embedded_report == external_report
        report_text_equal = (embedded_report.replace(b"\r\n", b"\n")
                             == external_report.replace(b"\r\n", b"\n"))
        require(report_text_equal, label + ": external/embedded report normalized text", errors)
        cad = json.loads(archive.read("design.json"))
        require(cad["physical_parameters_SI"] == receipt["result"]["design"],
                label + ": exported design matches receipt", errors)
    return {"directory": label, "valid": len(errors) == before,
            "receipt_sha256": sha256(external_receipt),
            "payload_sha256": receipt["payload_sha256"], "result_sha256": receipt["result_sha256"],
            "evidence_zip_sha256": sha256(path.read_bytes()),
            "report_html_sha256": sha256(external_report),
            "external_embedded_report_bytes_equal": report_bytes_equal,
            "external_embedded_report_lf_normalized_equal": report_text_equal,
            "archive_manifest": manifest,
            "software": receipt["software"]}


def audit_saved_traces(result, run_id, errors):
    """Recompute frozen-model force-balance diagnostics from stored audit traces."""
    traces = [a["trace"] for a in result["audit"]]
    mass = result["validation"]["known_primary_mass"]
    balance = [f - mass * a for trace in traces for f, a in zip(trace["force"], trace["a"])]
    xs = [x for trace in traces for x in trace["x"]]
    vs = [v for trace in traces for v in trace["v"]]
    scale = max(rms(balance), .1)
    output = []
    for model in result["models"]:
        p = model["parameters"]
        residual = [p["k"] * x + p["c"] * v + p.get("alpha", 0) * x ** 3
                    + p.get("friction", 0) * math.tanh(v / .04) - b
                    for x, v, b in zip(xs, vs, balance)]
        nrmse = rms(residual) / scale
        adequate = nrmse <= result["validation"]["audit_threshold"]
        close(nrmse, model["audit_nrmse"], run_id + ": audit " + model["name"], errors)
        require(adequate == model["adequate"], run_id + ": adequacy " + model["name"], errors)
        output.append({"run_id": run_id, **{key: result["config"][key] for key in ("world", "seed", "strategy")},
                       "model": model["name"], "weight": model["weight"],
                       "fit_rmse": model["fit_rmse"], "audit_nrmse": model["audit_nrmse"],
                       "recomputed_audit_nrmse": nrmse, "adequate": adequate,
                       **p, "included_in_design_pool": model["weight"] >= .025})
    return output


def analyze_result(receipt, errors):
    result = receipt["result"]
    c, v, s = result["config"], result["validation"], result["summary"]
    run_id = f"{c['world']}/{c['seed']}/{c['strategy']}"
    models = audit_saved_traces(result, run_id, errors)
    grid = result["design_grid"]
    selected_grid = grid[v["selected_grid_index"]]
    nominal_grid = grid[v["nominal_grid_index"]]
    require(v["design_grid_size"] == len(grid) == 30, run_id + ": grid size", errors)
    for key in PHYSICAL_KEYS:
        require(result["design"][key] == selected_grid[key], run_id + ": selected grid " + key, errors)
    reference = math.sqrt(math.fsum(m["weight"] * m["parameters"]["k"] for m in result["models"]) / mass_of(result))
    expected_grid = [{"mass": mass, "stiffness": mass * (reference * ratio) ** 2,
                      "damping": 2 * damping_ratio * mass * reference * ratio,
                      "tuning_ratio": ratio, "mass_ratio": mass / mass_of(result), "damping_ratio": damping_ratio}
                     for mass in (.08, .16) for ratio in (.75, .9, 1, 1.1, 1.25) for damping_ratio in (.05, .15, .3)]
    for index, (actual, expected) in enumerate(zip(grid, expected_grid)):
        for key in PHYSICAL_KEYS:
            close(actual[key], expected[key], f"{run_id}: grid formula {index} {key}", errors)
    challenges = []
    for index, challenge in enumerate(result["challenges"], 1):
        computed_reduction = reduction(challenge["baseline_rms"], challenge["design_rms"])
        close(computed_reduction, challenge["reduction_pct"], run_id + ": challenge reduction", errors)
        violation = (challenge["primary_peak"] > challenge["primary_peak_limit"]
                     or challenge["absorber_stroke_peak"] > challenge["absorber_stroke_limit"])
        require(violation == challenge["constraint_violation"], run_id + ": constraint flag", errors)
        require(challenge["oracle_rms"] <= challenge["design_rms"] + 1e-12,
                run_id + ": oracle lower bound", errors)
        row = {"run_id": run_id, **{key: c[key] for key in ("world", "seed", "strategy")},
               "challenge_index": index, **{key: value for key, value in challenge.items() if key != "tolerance"},
               **{"tolerance_" + key: value for key, value in challenge["tolerance"].items()},
               "recomputed_reduction_pct": computed_reduction,
               "nominal_reduction_pct": reduction(challenge["baseline_rms"], challenge["nominal_rms"]),
               "oracle_reduction_pct": reduction(challenge["baseline_rms"], challenge["oracle_rms"]),
               "oracle_gap_m": challenge["design_rms"] - challenge["oracle_rms"],
               "oracle_gap_reduction_pp": 100 * (challenge["design_rms"] - challenge["oracle_rms"]) / challenge["baseline_rms"],
               "relative_excess_over_oracle_pct": 100 * (challenge["design_rms"] / challenge["oracle_rms"] - 1),
               "selected_equals_nominal_rms": challenge["design_rms"] == challenge["nominal_rms"]}
        challenges.append(row)
    pooled = {kind: rms(challenge[kind + "_rms"] for challenge in result["challenges"])
              for kind in ("baseline", "design", "nominal", "oracle")}
    computed_reduction = reduction(pooled["baseline"], pooled["design"])
    for key in ("baseline", "design"):
        close(pooled[key], s[key + "_rms"], run_id + ": pooled " + key, errors)
    close(computed_reduction, s["reduction_pct"], run_id + ": pooled reduction", errors)
    close(min(row["reduction_pct"] for row in challenges), s["worst_reduction_pct"], run_id + ": worst reduction", errors)
    require(any(m["adequate"] for m in models) == s["adequate"], run_id + ": any-model adequacy", errors)
    require(sum(row["constraint_violation"] for row in challenges) == s["constraint_violations"],
            run_id + ": violation sum", errors)
    playback = result["playback"]
    window = [i for i, time in enumerate(playback["t"]) if time >= 7]
    close(rms(playback["baseline"][i] for i in window), challenges[0]["baseline_rms"], run_id + ": playback baseline RMS", errors)
    close(rms(playback["primary"][i] for i in window), challenges[0]["design_rms"], run_id + ": playback selected RMS", errors)
    close(max(abs(playback["primary"][i]) for i in window), challenges[0]["primary_peak"], run_id + ": playback primary peak", errors)
    close(max(abs(playback["absorber"][i] - playback["primary"][i]) for i in window),
          challenges[0]["absorber_stroke_peak"], run_id + ": playback stroke", errors)
    experiments = [{"run_id": run_id, **{key: c[key] for key in ("world", "seed", "strategy")},
                    **{key: experiment[key] for key in ("index", "frequency", "amplitude", "score", "reason")},
                    "trace_sha256": sha256(canonical(experiment["trace"])),
                    **{"weight_" + name: weight for name, weight in experiment["weights"].items()}}
                   for experiment in result["experiments"]]
    row = {"run_id": run_id, **c, "baseline_rms": pooled["baseline"], "design_rms": pooled["design"],
           "nominal_rms": pooled["nominal"], "oracle_rms": pooled["oracle"],
           "reduction_pct": computed_reduction, "saved_reduction_pct": s["reduction_pct"],
           "arithmetic_mean_challenge_reduction_pct": mean(x["reduction_pct"] for x in challenges),
           "worst_reduction_pct": min(x["reduction_pct"] for x in challenges),
           "best_challenge_reduction_pct": max(x["reduction_pct"] for x in challenges),
           "negative_challenge_count": sum(x["reduction_pct"] < 0 for x in challenges),
           "adequate": s["adequate"], "adequate_model_count": sum(x["adequate"] for x in models),
           "best_model": s["best_model"], "top_model_weight": max(x["weight"] for x in models),
           "design_pool_size": sum(x["included_in_design_pool"] for x in models),
           "constraint_violations": s["constraint_violations"], "solver_relative_error": v["solver_relative_error"],
           "selected_grid_index": v["selected_grid_index"], "nominal_grid_index": v["nominal_grid_index"],
           "selected_equals_nominal_physical_design": selected_grid == nominal_grid,
           "selected_equals_nominal_all_challenge_rms": all(x["selected_equals_nominal_rms"] for x in challenges),
           "oracle_reduction_pct": reduction(pooled["baseline"], pooled["oracle"]),
           "oracle_gap_m": pooled["design"] - pooled["oracle"],
           "oracle_gap_reduction_pp": 100 * (pooled["design"] - pooled["oracle"]) / pooled["baseline"],
           **{"design_" + key: result["design"][key] for key in PHYSICAL_KEYS},
           "result_sha256": receipt["result_sha256"]}
    return row, challenges, models, experiments


def mass_of(result):
    return result["validation"]["known_primary_mass"]


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def extremes(rows, key):
    lower = min(row[key] for row in rows)
    upper = max(row[key] for row in rows)
    return {"minimum": lower, "maximum": upper,
            "minimum_runs": [row["run_id"] for row in rows if row[key] == lower],
            "maximum_runs": [row["run_id"] for row in rows if row[key] == upper]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / "paper" / "data"
    benchmark = root / "runs" / "benchmark"
    errors, records, receipt_metadata = [], {}, []
    # Preserve the study evidence without fingerprinting unrelated UI history.
    original_paths = sorted(p for directory in (benchmark, root / "runs" / "example")
                            for p in directory.rglob("*"))
    original_hashes = {p.relative_to(root).as_posix(): sha256(p.read_bytes()) for p in original_paths if p.is_file()}
    source_paths = sorted((root / "counterform").glob("*.py"))
    current_source_digest = sha256(b"".join(p.name.encode() + p.read_bytes() for p in source_paths))
    source_hashes = {p.relative_to(root).as_posix(): sha256(p.read_bytes()) for p in source_paths}
    protocol_summary = json.loads((benchmark / "summary.json").read_text(encoding="utf-8"))
    protocol = protocol_summary["protocol"]
    rows, challenge_rows, model_rows, experiment_rows = [], [], [], []
    for world in protocol["worlds"]:
        for seed in protocol["seeds"]:
            for strategy in protocol["strategies"]:
                directory = benchmark / world / str(seed) / strategy
                receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
                receipt_metadata.append(verify_archive(directory, receipt, root, errors))
                config = receipt["config"]
                require(config == {"world": world, "seed": seed, "strategy": strategy,
                                   "budget": protocol["budget"], "noise": protocol["noise"]},
                        directory.as_posix() + ": protocol config", errors)
                row, challenges, models, experiments = analyze_result(receipt, errors)
                records[(world, seed, strategy)] = receipt["result"]
                rows.append(row)
                challenge_rows.extend(challenges)
                model_rows.extend(models)
                experiment_rows.extend(experiments)
    require(len(rows) == 16, "16 benchmark runs", errors)
    require(len(list(benchmark.glob("*/*/*/receipt.json"))) == len(rows), "no unlisted benchmark receipts", errors)
    by_key = {(row["world"], row["seed"], row["strategy"]): row for row in rows}
    csv_rows = list(csv.DictReader((benchmark / "results.csv").open(encoding="utf-8", newline="")))
    require(len(csv_rows) == len(rows), "results.csv row count", errors)
    for saved in csv_rows:
        row = by_key[(saved["world"], int(saved["seed"]), saved["strategy"])]
        for key, value in saved.items():
            if key in ("world", "strategy"):
                require(value == row[key], row["run_id"] + ": CSV " + key, errors)
            elif key == "adequate":
                require((value == "True") == row[key], row["run_id"] + ": CSV " + key, errors)
            else:
                close(float(value), row[key], row["run_id"] + ": CSV " + key, errors)
    groups = []
    for world in protocol["worlds"]:
        for strategy in protocol["strategies"]:
            group = [r for r in rows if r["world"] == world and r["strategy"] == strategy]
            item = {"world": world, "strategy": strategy, "n": len(group),
                    "mean_reduction_pct": mean(r["reduction_pct"] for r in group),
                    "min_reduction_pct": min(r["reduction_pct"] for r in group),
                    "max_reduction_pct": max(r["reduction_pct"] for r in group),
                    "mean_design_rms": mean(r["design_rms"] for r in group),
                    "adequacy_passes": sum(r["adequate"] for r in group),
                    "all_model_rejections": sum(not r["adequate"] for r in group),
                    "constraint_violations": sum(r["constraint_violations"] for r in group),
                    "negative_challenge_count": sum(r["negative_challenge_count"] for r in group),
                    "mean_pooled_oracle_reduction_pct": mean(r["oracle_reduction_pct"] for r in group),
                    "mean_pooled_oracle_gap_reduction_pp": mean(r["oracle_gap_reduction_pp"] for r in group)}
            saved = next(g for g in protocol_summary["comparisons"] if g["world"] == world and g["strategy"] == strategy)
            for key, value in saved.items():
                if key in ("world", "strategy"):
                    require(item[key] == value, f"{world}/{strategy}: summary {key}", errors)
                else:
                    close(item[key], value, f"{world}/{strategy}: summary {key}", errors)
            groups.append(item)
    paired = []
    for world in protocol["worlds"]:
        for seed in protocol["seeds"]:
            target = by_key[(world, seed, "counterform")]
            for comparator in ("active", "random", "passive"):
                control = by_key[(world, seed, comparator)]
                paired.append({"world": world, "seed": seed, "comparison": "counterform-minus-" + comparator,
                               "reduction_delta_pp": target["reduction_pct"] - control["reduction_pct"],
                               "design_rms_delta_m": target["design_rms"] - control["design_rms"],
                               "worst_reduction_delta_pp": target["worst_reduction_pct"] - control["worst_reduction_pct"]})
    paired_groups = []
    for world in protocol["worlds"]:
        for comparator in ("active", "random", "passive"):
            group = [p for p in paired if p["world"] == world and p["comparison"] == "counterform-minus-" + comparator]
            paired_groups.append({"world": world, "comparison": "counterform-minus-" + comparator, "n": len(group),
                                  **{name + "_" + key: fn(p[key] for p in group)
                                     for key in ("reduction_delta_pp", "design_rms_delta_m", "worst_reduction_delta_pp")
                                     for name, fn in (("mean", mean), ("min", min), ("max", max))}})
    coincidences, grid_comparisons, truths = [], [], []
    for world in protocol["worlds"]:
        for seed in protocol["seeds"]:
            active, cf = records[(world, seed, "active")], records[(world, seed, "counterform")]
            acq = lambda r: [(e["frequency"], e["amplitude"]) for e in r["experiments"]]
            item = {"world": world, "seed": seed, "acquisitions": acq(cf),
                    "acquisition_settings_exactly_equal": acq(active) == acq(cf),
                    "observations_exactly_equal": [e["trace"] for e in active["experiments"]] == [e["trace"] for e in cf["experiments"]],
                    "weights_at_every_step_exactly_equal": [e["weights"] for e in active["experiments"]] == [e["weights"] for e in cf["experiments"]],
                    **{key + "_exactly_equal": active[key] == cf[key] for key in
                       ("models", "design_grid", "design", "challenges", "summary", "response", "audit", "playback", "validation")},
                    "noninitial_cf_over_active_scores": [b["score"] / a["score"] for a, b in zip(active["experiments"][1:], cf["experiments"][1:])]}
            coincidences.append(item)
            for comparator in ("passive", "random", "active"):
                other = records[(world, seed, comparator)]
                grid_comparisons.append({"world": world, "seed": seed, "comparator": comparator,
                                         "full_grid_exactly_equal_to_counterform": other["design_grid"] == cf["design_grid"],
                                         "selected_physical_design_exactly_equal_to_counterform": all(other["design"][k] == cf["design"][k] for k in PHYSICAL_KEYS)})
            truths.append({"world": world, "seed": seed, **cf["ground_truth"],
                           "all_strategies_share_truth": all(records[(world, seed, strategy)]["ground_truth"] == cf["ground_truth"] for strategy in STRATEGIES)})
    shared_seed_parameters = [{"seed": seed, "k_c_alpha_shared_across_worlds": all(
        records[("cubic", seed, "counterform")]["ground_truth"][k] == records[("unmodelled", seed, "counterform")]["ground_truth"][k]
        for k in ("k", "c", "alpha"))} for seed in protocol["seeds"]]
    audit_summary = [{"world": world, "strategy": strategy,
                      "run_count": sum(r["world"] == world and r["strategy"] == strategy for r in rows),
                      "any_model_pass_count": sum(r["world"] == world and r["strategy"] == strategy and r["adequate"] for r in rows),
                      "all_model_reject_count": sum(r["world"] == world and r["strategy"] == strategy and not r["adequate"] for r in rows),
                      "candidate_evaluations": 6,
                      "candidate_pass_count": sum(m["world"] == world and m["strategy"] == strategy and m["adequate"] for m in model_rows)}
                     for world in protocol["worlds"] for strategy in STRATEGIES]
    example_receipt = json.loads((root / "runs" / "example" / "receipt.json").read_text(encoding="utf-8"))
    example_integrity = verify_archive(root / "runs" / "example", example_receipt, root, errors)
    example, example_challenges, example_models, example_experiments = analyze_result(example_receipt, errors)
    inputs_unchanged = True
    for path, digest in original_hashes.items():
        unchanged = sha256((root / path).read_bytes()) == digest
        inputs_unchanged = inputs_unchanged and unchanged
        require(unchanged, path + ": original evidence unchanged", errors)
    all_sources_match = all(x["software"]["source_sha256"] == current_source_digest for x in receipt_metadata + [example_integrity])
    require(all_sources_match, "saved/current package Python source digests match", errors)
    result = {
        "schema": "counterform.paper-analysis.v1",
        "analysis": {"script": "paper/analyze_results.py", "script_sha256": sha256(Path(__file__).read_bytes()),
                     "python": platform.python_version(), "dependencies": "Python standard library only",
                     "mode": "Saved evidence analysis; no engine import, fitting, simulation or numerical replay",
                     "rounding_tolerance": 1e-12, "input_files_unchanged": inputs_unchanged},
        "protocol": protocol,
        "units_and_aggregation": {
            "run_count": len(rows), "world_seed_instance_count": 4, "underlying_parameter_seed_count": 2,
            "challenge_evaluation_count": len(challenge_rows), "unique_world_seed_challenge_conditions": 12,
            "candidate_evaluations": len(model_rows), "acquisitions_per_run": 3, "acquisitions_total": len(experiment_rows),
            "audit_acquisitions_per_run": 2, "audit_samples_per_run": 842,
            "instrument_time_points_per_acquisition": 421, "rms_samples_per_challenge": 211,
            "pooled_rms_formula": "sqrt(mean(challenge_RMS**2)) over three equal-length 7-14 s sampled windows",
            "run_reduction_formula": "100*(1-pooled_design_RMS/pooled_baseline_RMS)",
            "world_strategy_mean_formula": "arithmetic mean of two per-run pooled-RMS reductions; not pooled across seeds",
            "paired_delta_direction": "COUNTERFORM minus comparator; positive reduction delta favors COUNTERFORM",
            "oracle_definition": "Retrospective minimum separately per challenge in that run's fitted-reference 30-design grid; unconstrained; oracle may use a different design at every challenge",
            "statistical_scope": "Descriptive only; two shared parameter seeds, no confidence intervals, p-values or population efficacy claims"},
        "integrity": {"benchmark_receipts_checked": len(receipt_metadata), "benchmark_bundles_checked": len(receipt_metadata),
                      "all_benchmark_valid": all(r["valid"] for r in receipt_metadata),
                      "example_valid": example_integrity["valid"], "errors": errors,
                      "current_package_source_sha256": current_source_digest, "all_saved_source_digests_match_current": all_sources_match,
                      "current_source_file_hashes": source_hashes,
                      "summary_json_sha256": sha256((benchmark / "summary.json").read_bytes()),
                      "results_csv_sha256": sha256((benchmark / "results.csv").read_bytes()),
                      "representation_notes": ["All external report.html files use CRLF and embedded reports use LF; raw report hashes differ, but normalized report text is identical. Original evidence was preserved."],
                      "original_runs_file_hashes": original_hashes,
                      "scope": "Checksums and arithmetic consistency, not author authentication or simulator numerical replay"},
        "receipt_metadata": receipt_metadata, "runs": rows, "challenges": challenge_rows,
        "models": model_rows, "experiments": experiment_rows, "world_strategy_summary": groups,
        "paired_deltas": paired, "paired_delta_summary": paired_groups,
        "active_counterform_coincidence": coincidences, "grid_comparisons": grid_comparisons,
        "truths": truths, "shared_seed_parameters": shared_seed_parameters, "audit_summary": audit_summary,
        "audit_diagnostics": {
            "all_model_rejections_total": sum(not r["adequate"] for r in rows),
            "any_model_passes_total": sum(r["adequate"] for r in rows),
            "candidate_passes_total": sum(m["adequate"] for m in model_rows),
            "candidate_rejections_total": sum(not m["adequate"] for m in model_rows),
            "omitted_law_any_model_acceptances": [r["run_id"] for r in rows if r["world"] == "unmodelled" and r["adequate"]],
            "omitted_law_accepted_models": [m for m in model_rows if m["world"] == "unmodelled" and m["adequate"]],
            "in_library_all_model_rejections": [r["run_id"] for r in rows if r["world"] == "cubic" and not r["adequate"]],
            "interpretation": "An omitted-law pass is acceptance of an approximate finite candidate on the fixed diagnostic, not recovery of the true law; in-library rejection concerns the acquired fit, not impossibility of the model family."},
        "extrema": {key: extremes(rows, key) for key in ("reduction_pct", "worst_reduction_pct", "solver_relative_error", "top_model_weight", "oracle_gap_reduction_pp")},
        "challenge_extrema": {"reduction_pct_min": min(c["reduction_pct"] for c in challenge_rows),
                              "reduction_pct_max": max(c["reduction_pct"] for c in challenge_rows),
                              "negative_count": sum(c["reduction_pct"] < 0 for c in challenge_rows),
                              "negative_runs": sum(r["negative_challenge_count"] > 0 for r in rows),
                              "primary_peak_max": max(c["primary_peak"] for c in challenge_rows),
                              "absorber_stroke_peak_max": max(c["absorber_stroke_peak"] for c in challenge_rows),
                              "oracle_gap_m_min": min(c["oracle_gap_m"] for c in challenge_rows),
                              "oracle_gap_m_max": max(c["oracle_gap_m"] for c in challenge_rows),
                              "oracle_gap_reduction_pp_min": min(c["oracle_gap_reduction_pp"] for c in challenge_rows),
                              "oracle_gap_reduction_pp_max": max(c["oracle_gap_reduction_pp"] for c in challenge_rows)},
        "design_diagnostics": {"selected_nominal_identical_physical_design_count": sum(r["selected_equals_nominal_physical_design"] for r in rows),
                               "selected_nominal_identical_challenge_rms_count": sum(c["selected_equals_nominal_rms"] for c in challenge_rows),
                               "design_pool_size_counts": dict(Counter(str(r["design_pool_size"]) for r in rows)),
                               "grid_interpretation": "All runs share a 30-entry combinatorial rule; physical stiffness and damping depend on fitted weighted stiffness. It is not an identical physical grid across strategies."},
        "separate_example": {"excluded_from_benchmark": True, "integrity": example_integrity, "run": example,
                             "challenges": example_challenges, "models": example_models, "experiments": example_experiments},
        "caveats": [
            "Identical active/COUNTERFORM behavior in four saved instances cannot establish that the decision heuristic is generally ineffective; the policies were not behaviorally separated here.",
            "Oracle gaps combine search approximation, grid restrictions and task mismatch; each challenge receives a retrospective oracle choice, not one attainable common oracle design.",
            "The source reports DOP853/Radau discrepancy on the first selected-design challenge only; this analysis verifies the saved value's provenance, not a fresh integration.",
            "Only the first held-out playback trajectory is saved; the remaining challenge RMS values are checked algebraically but not recomputed from trajectories.",
            "Source equality and checksums establish consistency with saved metadata; coordinated edits could rewrite all checksums.",
            "Fixed audit threshold .1 is an engineering diagnostic, not a calibrated model-class test, false-acceptance rate estimate or significance test.",
            "The benchmark contains no linear or pure-friction world, uses only two parameter seeds, one noise level and one three-acquisition budget.",
            "World-seed pairs share k,c,alpha and seeded noise conventions; 16 runs and 48 challenge evaluations are not 16 or 48 independent replicates.",
            "The separate five-acquisition seed42 example is illustrative and excluded from the equal-budget benchmark.",
            "All reductions are conditional on synthetic instrumented dynamics, the three fixed challenge protocols, finite 30-design grids and sampled 7-14 s RMS windows; no physical deployment claims follow."]}
    output.mkdir(parents=True, exist_ok=True)
    for name, values in (("runs.csv", rows), ("challenges.csv", challenge_rows), ("models.csv", model_rows),
                         ("experiments.csv", experiment_rows), ("world_strategy_summary.csv", groups),
                         ("paired_deltas.csv", paired), ("paired_delta_summary.csv", paired_groups)):
        write_csv(output / name, values)
    (output / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"benchmark_runs": len(rows), "challenge_evaluations": len(challenge_rows),
                      "benchmark_integrity_valid": result["integrity"]["all_benchmark_valid"],
                      "consistency_errors": len(errors), "output": str(output)}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
