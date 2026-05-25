"""Minimal SARIF 2.1.0 emitter so reports can be loaded into VS Code's Problems view."""

from __future__ import annotations

import json

from codesentinel.schema import ReviewResult, Severity

_SEV_TO_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}


def to_sarif(result: ReviewResult | list[ReviewResult]) -> str:
    results = result if isinstance(result, list) else [result]
    sarif_results = []
    rules: dict[str, dict] = {}

    for r in results:
        for f in r.findings:
            rule_id = f.rule_id or f"codesentinel/{f.category.value}/{f.severity.value}"
            rules.setdefault(
                rule_id,
                {
                    "id": rule_id,
                    "name": rule_id.replace("/", "-"),
                    "shortDescription": {"text": f.title[:120]},
                    "fullDescription": {"text": f.description[:1000]},
                    "defaultConfiguration": {"level": _SEV_TO_LEVEL.get(f.severity, "note")},
                },
            )
            sarif_results.append(
                {
                    "ruleId": rule_id,
                    "level": _SEV_TO_LEVEL.get(f.severity, "note"),
                    "message": {"text": f"{f.title}: {f.description}"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": r.file_path},
                                "region": {
                                    "startLine": f.line_start,
                                    "endLine": f.line_end,
                                },
                            }
                        }
                    ],
                }
            )

    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CodeSentinel",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/lindavlr/codesentinel-ai",
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)
