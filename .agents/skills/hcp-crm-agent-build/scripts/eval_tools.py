"""
Standing evaluation harness for the 5 LangGraph tools in the HCP CRM agent.

Run this after ANY change to backend/app/agent/ — not just at the end of a
session. It calls each tool independently of the frontend and asserts on
structured output, not on "it looked right in the demo."

Usage:
    python scripts/eval_tools.py
    python scripts/eval_tools.py --tool edit_interaction   # run one case only
    python scripts/eval_tools.py --verbose                 # print full I/O

Exit code is non-zero if any assertion fails — wire this into a pre-commit
hook or CI step once the backend exists.
"""

import argparse
import sys
import json
from dataclasses import dataclass, field
from typing import Callable, Any

# Adjust this import to match your actual project layout once Phase 3 exists.
# from backend.app.agent.graph import run_agent_turn

RESULTS = {"passed": 0, "failed": 0}


@dataclass
class EvalCase:
    name: str
    tool: str
    setup_form_state: dict = field(default_factory=dict)
    message: str = ""
    assertions: list = field(default_factory=list)  # list of (label, fn(result) -> bool)


def check(label: str, condition: bool, verbose: bool = False):
    status = "PASS" if condition else "FAIL"
    RESULTS["passed" if condition else "failed"] += 1
    print(f"  [{status}] {label}")
    return condition


def run_case(case: EvalCase, run_agent_turn: Callable[[dict, str], Any], verbose: bool = False):
    print(f"\n=== {case.name} ({case.tool}) ===")
    result = run_agent_turn(case.setup_form_state, case.message)

    if verbose:
        print("  Input message:", case.message)
        print("  Result:", json.dumps(result, indent=2, default=str))

    for label, assertion_fn in case.assertions:
        try:
            check(label, assertion_fn(result), verbose)
        except Exception as e:
            check(f"{label} (raised {type(e).__name__}: {e})", False, verbose)


def fields_unchanged(before: dict, after: dict, except_keys: set) -> bool:
    """Assert every key not in except_keys is unchanged between before/after."""
    for k, v in before.items():
        if k in except_keys:
            continue
        if after.get(k) != v:
            print(f"    -> unexpected change on '{k}': {v!r} -> {after.get(k)!r}")
            return False
    return True


CASES = [
    EvalCase(
        name="log_interaction populates all expected fields",
        tool="log_interaction",
        message=(
            "Today I met with Dr. Alice Jones and discussed product X efficacy. "
            "The sentiment was positive and I shared the brochures."
        ),
        assertions=[
            ("hcp_name resolved", lambda r: r["interaction_form"].get("hcp_name") not in (None, "")),
            ("interaction_type set", lambda r: r["interaction_form"].get("interaction_type") not in (None, "")),
            ("date set", lambda r: r["interaction_form"].get("date") not in (None, "")),
            ("topics_discussed populated", lambda r: bool(r["interaction_form"].get("topics_discussed"))),
            ("sentiment == positive", lambda r: r["interaction_form"].get("sentiment") == "positive"),
            ("materials_shared includes brochures", lambda r: "brochure" in json.dumps(r["interaction_form"].get("materials_shared", [])).lower()),
            ("tool_trace logged this call", lambda r: any(t["tool_name"] == "log_interaction" for t in r.get("tool_trace", []))),
        ],
    ),
    EvalCase(
        name="edit_interaction patches ONLY mentioned fields",
        tool="edit_interaction",
        setup_form_state={
            "hcp_name": "Dr. Smith",
            "sentiment": "positive",
            "topics_discussed": "Product X efficacy",
            "materials_shared": ["brochures"],
            "date": "2026-07-16",
        },
        message="Sorry, the name was actually Dr. John and the sentiment was negative.",
        assertions=[
            ("hcp_name changed to Dr. John", lambda r: "john" in r["interaction_form"].get("hcp_name", "").lower()),
            ("sentiment changed to negative", lambda r: r["interaction_form"].get("sentiment") == "negative"),
            (
                "all other fields untouched",
                lambda r: fields_unchanged(
                    {
                        "topics_discussed": "Product X efficacy",
                        "materials_shared": ["brochures"],
                        "date": "2026-07-16",
                    },
                    r["interaction_form"],
                    except_keys={"hcp_name", "sentiment"},
                ),
            ),
        ],
    ),
    EvalCase(
        name="check_compliance flags a risky claim and does not block",
        tool="check_compliance",
        setup_form_state={
            "topics_discussed": "Told the HCP this drug cures all forms of the disease with no side effects",
            "outcomes": "HCP seemed convinced",
        },
        message="",  # runs automatically post-log in the real graph; call directly for this eval
        assertions=[
            ("compliance_flag == review", lambda r: r["interaction_form"].get("compliance_flag") == "review"),
            ("rationale present", lambda r: bool(r["interaction_form"].get("compliance_rationale"))),
            ("save is not blocked", lambda r: r.get("blocked", False) is False),
        ],
    ),
    EvalCase(
        name="suggest_next_action returns a real list, not a hardcoded string",
        tool="suggest_next_action",
        setup_form_state={
            "sentiment": "positive",
            "outcomes": "Dr. Smith asked for a follow-up call next month",
        },
        message="",
        assertions=[
            ("suggested_follow_ups is a non-empty list", lambda r: isinstance(r["interaction_form"].get("suggested_follow_ups"), list) and len(r["interaction_form"]["suggested_follow_ups"]) > 0),
            ("suggestion text is not a static placeholder", lambda r: r["interaction_form"]["suggested_follow_ups"][0] not in ("TODO", "N/A", "")),
        ],
    ),
    EvalCase(
        name="retrieve_interaction_history asks a clarifying question on ambiguity",
        tool="retrieve_interaction_history",
        message="What did we last discuss with Dr. Smith?",
        assertions=[
            ("no form fields were touched", lambda r: r["interaction_form"] == {}),
            ("response is a chat message, not a silent guess", lambda r: bool(r.get("chat_response"))),
            # With 2+ seeded "Dr. Smith" HCPs, this should read as a question, not a flat answer.
            ("response looks like a clarifying question", lambda r: "?" in r.get("chat_response", "")),
        ],
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", help="Run only cases for this tool name")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        from backend.app.agent.graph import run_agent_turn  # noqa: F401
    except ImportError as e:
        print(f"Error importing run_agent_turn: {e}")
        print(
            "Could not import run_agent_turn from backend.app.agent.graph.\n"
            "This script is a template — wire the import above to your actual "
            "Phase 3 module once it exists, then re-run."
        )
        sys.exit(2)

    cases = [c for c in CASES if args.tool is None or c.tool == args.tool]
    if not cases:
        print(f"No eval cases found for tool '{args.tool}'")
        sys.exit(1)

    for case in cases:
        run_case(case, run_agent_turn, verbose=args.verbose)

    print(f"\n{'='*40}\n{RESULTS['passed']} passed, {RESULTS['failed']} failed\n{'='*40}")
    sys.exit(1 if RESULTS["failed"] else 0)


if __name__ == "__main__":
    main()
