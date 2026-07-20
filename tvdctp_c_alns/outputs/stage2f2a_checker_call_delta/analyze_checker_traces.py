from __future__ import annotations

import csv
import difflib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MODES = ("paper", "extended")


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def stable_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"relative_time_ns", "version", "direct_caller_line"}
    }


def alignment_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record["execution_phase"],
        Path(record["direct_caller_file"]).name,
        record["direct_caller_function"],
        record["action_id"],
        record["iteration"],
        record["state_business_fingerprint_before"],
        tuple(record["unassigned_customer_ids"]),
        record["active_context_present"],
        record["context_type"],
        record["checker_result"],
        record["normalized_violation_signature"],
    )


def coarse_correspondence_key(record: dict[str, Any]) -> tuple[Any, ...]:
    """Identify the same semantic boundary even when its State changed."""
    return (
        record["execution_phase"],
        Path(record["direct_caller_file"]).name,
        record["direct_caller_function"],
        record["action_id"],
        record["iteration"],
        record["checker_result"],
        record["normalized_violation_signature"],
        record["objective_call_index"],
    )


def write_trace_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = list(records[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: (
                        json.dumps(value, ensure_ascii=False, sort_keys=True)
                        if isinstance(value, (dict, list))
                        else value
                    )
                    for key, value in record.items()
                }
            )


def main() -> None:
    result: dict[str, Any] = {}
    for mode in MODES:
        baseline1 = load(f"baseline_{mode}_run1.json")
        baseline2 = load(f"baseline_{mode}_run2.json")
        current1 = load(f"current_{mode}_run1.json")
        current2 = load(f"current_{mode}_run2.json")
        baseline_trace = baseline1["trace"]
        current_trace = current1["trace"]

        write_trace_csv(ROOT / f"{mode}_checker_trace_baseline.csv", baseline_trace)
        write_trace_csv(ROOT / f"{mode}_checker_trace_current.csv", current_trace)

        baseline_deterministic = [stable_record(row) for row in baseline_trace] == [
            stable_record(row) for row in baseline2["trace"]
        ]
        current_deterministic = [stable_record(row) for row in current_trace] == [
            stable_record(row) for row in current2["trace"]
        ]

        baseline_keys = [alignment_key(row) for row in baseline_trace]
        current_keys = [alignment_key(row) for row in current_trace]
        matcher = difflib.SequenceMatcher(
            a=baseline_keys, b=current_keys, autojunk=False
        )
        opcodes = matcher.get_opcodes()
        non_equal = [opcode for opcode in opcodes if opcode[0] != "equal"]
        inserted: list[dict[str, Any]] = []
        deleted: list[dict[str, Any]] = []
        replaced: list[dict[str, Any]] = []
        for tag, i1, i2, j1, j2 in non_equal:
            if tag == "insert":
                inserted.extend(current_trace[j1:j2])
            elif tag == "delete":
                deleted.extend(baseline_trace[i1:i2])
            else:
                replaced.append(
                    {
                        "baseline_range": [i1 + 1, i2],
                        "current_range": [j1 + 1, j2],
                        "baseline": baseline_trace[i1:i2],
                        "current": current_trace[j1:j2],
                    }
                )

        first_divergence = None
        if non_equal:
            tag, i1, i2, j1, j2 = non_equal[0]
            first_divergence = {
                "tag": tag,
                "baseline_range": [i1 + 1, i2],
                "current_range": [j1 + 1, j2],
                "baseline_before": baseline_trace[i1 - 1] if i1 else None,
                "current_before": current_trace[j1 - 1] if j1 else None,
                "baseline_after": baseline_trace[i2] if i2 < len(baseline_trace) else None,
                "current_after": current_trace[j2] if j2 < len(current_trace) else None,
            }

        extra = inserted[0] if len(inserted) == 1 and not deleted and not replaced else None
        corresponding_baseline = None
        corresponding_current = None
        replacement_block_realigns = False
        if len(non_equal) == 1 and non_equal[0][0] == "replace":
            _, i1, i2, j1, j2 = non_equal[0]
            if i2 - i1 == 1 and j2 - j1 == 2:
                corresponding_baseline = baseline_trace[i1]
                corresponding_current = current_trace[j2 - 1]
                if coarse_correspondence_key(corresponding_baseline) == coarse_correspondence_key(
                    corresponding_current
                ):
                    extra = current_trace[j1]
                    replacement_block_realigns = True
        previous_equivalent = None
        if extra is not None:
            extra_index = int(extra["call_index"]) - 1
            for prior in reversed(current_trace[:extra_index]):
                if (
                    prior["state_business_fingerprint_before"]
                    == extra["state_business_fingerprint_before"]
                    and prior["checker_result"] == extra["checker_result"]
                    and prior["normalized_violation_signature"]
                    == extra["normalized_violation_signature"]
                ):
                    previous_equivalent = prior
                    break

        result[mode] = {
            "baseline_count": len(baseline_trace),
            "current_count": len(current_trace),
            "delta": len(current_trace) - len(baseline_trace),
            "baseline_trace_deterministic": baseline_deterministic,
            "current_trace_deterministic": current_deterministic,
            "matching_blocks": [list(block) for block in matcher.get_matching_blocks()],
            "non_equal_opcodes": [list(opcode) for opcode in non_equal],
            "inserted_count": len(inserted),
            "deleted_count": len(deleted),
            "replacement_count": len(replaced),
            "first_divergence": first_divergence,
            "extra_call": extra,
            "corresponding_baseline_call": corresponding_baseline,
            "corresponding_current_call": corresponding_current,
            "previous_equivalent_check": previous_equivalent,
            "sequence_realigns_after_extra": (
                (len(inserted) == 1 and not deleted and not replaced)
                or replacement_block_realigns
            ),
            "pure_insertion_under_state_aware_key": (
                len(inserted) == 1 and not deleted and not replaced
            ),
            "one_to_two_replacement_block": replacement_block_realigns,
            "behavior_neutral_checks": {
                "baseline_run1": baseline1["behavior_neutral_checks"],
                "baseline_run2": baseline2["behavior_neutral_checks"],
                "current_run1": current1["behavior_neutral_checks"],
                "current_run2": current2["behavior_neutral_checks"],
            },
            "run_summaries": {
                key: {
                    item: value[item]
                    for item in (
                        "trace_count",
                        "profile_checker_calls",
                        "profile_objective_calls",
                        "rng_digest",
                        "final_objective",
                        "final_fingerprint",
                        "history",
                    )
                }
                for key, value in {
                    "baseline_run1": baseline1,
                    "baseline_run2": baseline2,
                    "current_run1": current1,
                    "current_run2": current2,
                }.items()
            },
        }

    paper_extra = result["paper"]["extra_call"]
    extended_extra = result["extended"]["extra_call"]
    result["cross_mode"] = {
        "both_extra_calls_identified": bool(paper_extra and extended_extra)
    }
    if paper_extra and extended_extra:
        result["cross_mode"].update(
            {
                "same_direct_caller": (
                    paper_extra["direct_caller_file"],
                    paper_extra["direct_caller_function"],
                )
                == (
                    extended_extra["direct_caller_file"],
                    extended_extra["direct_caller_function"],
                ),
                "same_stack_signature": paper_extra["compact_stack_signature"]
                == extended_extra["compact_stack_signature"],
                "same_execution_phase": paper_extra["execution_phase"]
                == extended_extra["execution_phase"],
                "same_state_classification": paper_extra["state_classification"]
                == extended_extra["state_classification"],
            }
        )
    (ROOT / "trace_alignment_summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
