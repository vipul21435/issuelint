from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from issuelint.agreement import (
    agreement,
    auc,
    bootstrap_auc,
    format_agreement,
    load_findings,
    load_labels,
)
from issuelint.checks import run_all
from issuelint.cli import main
from issuelint.records import TaskRecord


def _pairwise_auc(scores, labels):
    pos = [s for s, y in zip(scores, labels, strict=True) if y]
    neg = [s for s, y in zip(scores, labels, strict=True) if not y]
    total = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return total / (len(pos) * len(neg))


def test_auc_extremes_and_chance():
    assert auc([0.1, 0.2, 0.8, 0.9], [False, False, True, True]) == 1.0
    assert auc([0.9, 0.8, 0.2, 0.1], [False, False, True, True]) == 0.0
    assert auc([0.5, 0.5, 0.5, 0.5], [False, True, False, True]) == 0.5


@pytest.mark.parametrize("seed", range(20))
def test_auc_matches_pair_counting_with_ties(seed):
    rng = random.Random(seed)
    n = rng.randint(4, 40)
    scores = [rng.choice([0.0, 0.25, 0.5, 0.75, 1.0]) for _ in range(n)]
    labels = [rng.random() < 0.4 for _ in range(n)]
    labels[0], labels[1] = True, False
    assert auc(scores, labels) == pytest.approx(_pairwise_auc(scores, labels))
    # A strictly increasing transform of the scores leaves the AUC unchanged.
    assert auc([3 * s + 1 for s in scores], labels) == pytest.approx(auc(scores, labels))


def test_auc_rejects_one_class_and_length_mismatch():
    with pytest.raises(ValueError, match="positive"):
        auc([1.0, 2.0], [True, True])
    with pytest.raises(ValueError, match="length"):
        auc([1.0], [True, False])


def test_bootstrap_interval_contains_the_estimate_on_separable_data():
    rng = random.Random(1)
    labels = [i % 2 == 0 for i in range(200)]
    scores = [rng.gauss(1.0 if y else 0.0, 1.0) for y in labels]
    lo, hi = bootstrap_auc(scores, labels, resamples=300)
    est = auc(scores, labels)
    assert lo <= est <= hi
    assert 0.6 < lo < hi < 0.9
    with pytest.raises(ValueError, match="resample"):
        bootstrap_auc([1.0, 2.0], [True, False], resamples=0)


def _labelled(tmp_path: Path):
    vague = "it does not work"
    clear = (
        "Calling parse('1,2') should return [1, 2] but it raises ValueError: bad input.\n"
        "Steps to reproduce:\n```\nparse('1,2')\n```\nTraceback (most recent call last): ..."
    )
    records = [TaskRecord(id=f"t{i}", issue=vague if i % 2 else clear, patch="") for i in range(10)]
    findings = tmp_path / "f.json"
    findings.write_text(json.dumps([r.as_dict() for r in run_all(records)]), encoding="utf-8")
    labels = tmp_path / "labels.csv"
    with labels.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle)
        w.writerow(["instance_id", "underspecified"])
        for i in range(10):
            w.writerow([f"t{i}", 3 if i % 2 else 0])
        w.writerow(["unknown", ""])
    return findings, labels


def test_agreement_on_a_separable_toy_set(tmp_path: Path):
    findings, labels_path = _labelled(tmp_path)
    labels = load_labels(labels_path, "underspecified")
    assert len(labels) == 10
    rows = {r.name: r for r in agreement(json.loads(findings.read_text()), labels, 2, 200)}
    under = rows["underspecification"]
    assert under.auc == 1.0
    assert under.flagged_positive == 1.0
    assert under.flagged_negative == 0.0
    assert rows["underspecification.tokens"].auc == 0.0
    assert rows["underspecification.tokens"].flagged_positive is None
    assert "solution_leakage" not in rows  # constant score
    text = format_agreement(list(rows.values()), "underspecified", 2)
    assert "10 tasks, 5 positive" in text
    assert format_agreement([], "x", 1).startswith("no score")


def test_agree_command(tmp_path: Path, capsys):
    findings, labels = _labelled(tmp_path)
    args = ["agree", str(findings), str(labels), "--label", "underspecified", "--positive-at", "2"]
    assert main([*args, "--resamples", "50"]) == 0
    assert "underspecification" in capsys.readouterr().out
    assert main(["agree", str(findings), str(labels), "--label", "missing"]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="list"):
        load_findings(bad)


def test_labels_csv_with_a_byte_order_mark(tmp_path: Path):
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbfinstance_id,l\na,1\n")
    assert load_labels(path, "l") == {"a": 1.0}


def test_agree_reports_when_no_id_matches(tmp_path: Path, capsys):
    findings, _ = _labelled(tmp_path)
    labels = tmp_path / "other.csv"
    labels.write_text("instance_id,underspecified\nzz,3\nyy,0\n", encoding="utf-8")
    assert main(["agree", str(findings), str(labels), "--label", "underspecified"]) == 2
    assert "no task id" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["nan", "inf"])
def test_non_finite_labels_and_scores_are_rejected(tmp_path: Path, value: str):
    path = tmp_path / "l.csv"
    path.write_text(f"instance_id,l\na,{value}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        load_labels(path, "l")
    findings = tmp_path / "f.json"
    report = {"id": "a", "findings": [{"check": "c", "score": float(value), "flagged": False}]}
    findings.write_text(json.dumps([report]), encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        load_findings(findings)


def test_auc_rejects_nan_scores():
    with pytest.raises(ValueError, match="finite"):
        auc([float("nan"), 1.0, 0.0, 0.5], [True, False, False, True])
