#!/usr/bin/env python3
"""Compare findings returned by the API with expected.json for this scenario.

Usage:
  python check_expected.py findings.json [expected.json]

findings.json = the JSON body of GET /api/findings (a list) or GET /api/findings/report
(an object with a "findings" list). Save it from the browser DevTools Network tab
(Response -> copy) or with curl and a bearer token.

Exit code 0 = every expectation met, 1 = at least one FAIL. WARN lines (wrong severity or
an impact amount outside the listed alternatives) do not fail the run but need a look.
"""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


def norm_term(value) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def term_matches(finding_term, wanted: str) -> bool:
    t, w = norm_term(finding_term), norm_term(wanted)
    if not t:
        return False
    aliases = {"fall2026": {"fall2026", "fa26", "fall26"}, "spring2027": {"spring2027", "sp27", "spring27", "springsemester2027"}}
    return t in aliases.get(w, {w}) or w in t


def rule_matches(rule_id: str, pattern: str) -> bool:
    return rule_id.startswith(pattern[:-1]) if pattern.endswith("*") else rule_id == pattern


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return None


def main() -> int:
    findings_path = Path(sys.argv[1])
    expected_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("expected.json")
    raw = json.loads(findings_path.read_text(encoding="utf-8"))
    findings = raw["findings"] if isinstance(raw, dict) else raw
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    failures = warnings = 0

    print(f"{len(findings)} findings received; intended 'today' = {expected['today']}\n")
    print("EXPECTED FINDINGS")
    for exp in expected["expected_findings"]:
        candidates = [
            f for f in findings
            if rule_matches(f.get("rule_id", ""), exp["rule_id"])
            and (exp["term"] is None or term_matches(f.get("term"), exp["term"]))
        ]
        if not candidates:
            print(f"  FAIL {exp['id']} {exp['rule_id']} [{exp['term']}]: no matching finding")
            failures += 1
            continue
        best = next((f for f in candidates if f.get("severity") == exp["severity"]), candidates[0])
        notes = []
        if best.get("severity") != exp["severity"]:
            notes.append(f"severity {best.get('severity')} (expected {exp['severity']})")
        allowed = [money(a) for a in exp["impact_amount_any_of"]]
        got = money(best.get("impact_amount"))
        if allowed and got not in allowed:
            notes.append(f"impact {got} not in {[str(a) for a in allowed]}")
        if notes:
            warnings += 1
            print(f"  WARN {exp['id']} {best['rule_id']}: " + "; ".join(notes))
        else:
            print(f"  PASS {exp['id']} {best['rule_id']}")

    print("\nEXPECTED ABSENCES")
    for ab in expected["expected_absent"]:
        hits = []
        for f in findings:
            rid = f.get("rule_id", "")
            by_prefix = "rule_prefix" in ab and rid.startswith(ab["rule_prefix"])
            by_ids = rid in ab.get("rule_ids", [])
            if not (by_prefix or by_ids):
                continue
            if "term" in ab and not term_matches(f.get("term"), ab["term"]):
                continue
            hits.append(f)
        limit = ab.get("max_count", 0)
        if "max_count_for_term" in ab:
            term, limit = next(iter(ab["max_count_for_term"].items()))
            hits = [f for f in hits if term_matches(f.get("term"), term)]
        if len(hits) > limit:
            titles = "; ".join(f"{h.get('rule_id')}: {h.get('title')}" for h in hits[:3])
            print(f"  FAIL {ab['id']}: {ab['description']}\n       found {len(hits)} (allowed {limit}): {titles}")
            failures += 1
        else:
            print(f"  PASS {ab['id']}")

    infos = sum(1 for f in findings if f.get("severity") == "info")
    cap = expected["limits"]["max_default_info_findings"]
    print("\nNOISE")
    if infos > cap:
        print(f"  FAIL {infos} info findings (default cap {cap})")
        failures += 1
    else:
        print(f"  PASS {infos} info findings (cap {cap})")

    print(f"\n{failures} failure(s), {warnings} warning(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
