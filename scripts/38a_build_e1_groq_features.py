"""Build E1 Groq downstream dataset and features."""
from __future__ import annotations

import csv, hashlib, importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/final/master_text_dataset.csv"
GEN = ROOT / "data/interim/e1_free_model_replication/groq_generation"
OUT = ROOT / "data/interim/e1_free_model_replication/groq_downstream"
META = ROOT / "metadata"
LOGS = ROOT / "logs"

spec = importlib.util.spec_from_file_location("fh", ROOT / "scripts/13_extract_stylometric_features.py")
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)  # type: ignore[union-attr]

MODELS = {
    "groq_llama_3_3_70b_free": "Groq Llama 3.3 70B",
    "groq_qwen_32b_free": "Groq Qwen 32B",
    "groq_gpt_oss_120b_free": "Groq GPT-OSS 120B",
}
AUTHORS = ["austen", "dickens", "poe", "shelley", "twain", "wilde"]
CONDITIONS = ["original", "paraphrase", "modernize", "simplify"]
SPLIT_COUNTS = {"train": 14, "validation": 3, "test": 3}

MASTER_OUT = OUT / "e1_groq_master_text_dataset.csv"
FEATURES_OUT = OUT / "e1_groq_stylometric_features.csv"
FEATURE_REGISTRY = META / "e1_groq_feature_registry.csv"
SPLIT_SUMMARY = META / "e1_groq_split_summary.csv"
BUILD_REPORT = LOGS / "e1_groq_feature_build_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def original_map() -> dict[str, dict[str, str]]:
    return {r["passage_id"]: r for r in read_csv(MASTER) if r.get("condition") == "original"}


def split_map(originals: list[dict[str, str]]) -> dict[str, str]:
    by_author: dict[str, list[str]] = defaultdict(list)
    for r in originals:
        if r["passage_id"] not in by_author[r["author_id"]]:
            by_author[r["author_id"]].append(r["passage_id"])
    out: dict[str, str] = {}
    for author in AUTHORS:
        ids = sorted(by_author[author])
        if len(ids) != 20:
            raise RuntimeError(f"Expected 20 passages for {author}, found {len(ids)}")
        idx = 0
        for split, count in SPLIT_COUNTS.items():
            for pid in ids[idx:idx+count]: out[pid] = split
            idx += count
    return out


def build_master_rows() -> list[dict[str, Any]]:
    omap = original_map(); rows: list[dict[str, Any]] = []
    for model_id, label in MODELS.items():
        parsed_path = GEN / model_id / "parsed_outputs.csv"
        parsed = read_csv(parsed_path)
        if len(parsed) != 360:
            raise RuntimeError(f"{model_id}: expected 360 parsed rows, found {len(parsed)}")
        pids = sorted({r["passage_id"] for r in parsed})
        if len(pids) != 120:
            raise RuntimeError(f"{model_id}: expected 120 passages, found {len(pids)}")
        smap = split_map([omap[p] for p in pids])
        for pid in pids:
            o = omap[pid]; text = o["text"]
            rows.append({
                "analysis_model_id": model_id, "analysis_model_label": label,
                "text_id": f"{model_id}|original|{pid}", "passage_id": pid, "condition": "original",
                "author_id": o["author_id"], "author_name": o["author_name"],
                "work_id": o["work_id"], "work_title": o["work_title"], "split": smap[pid],
                "qc_status": "pass", "qc_flags": "", "text_sha256": sha_text(text), "text": text,
            })
        for r in parsed:
            o = omap[r["passage_id"]]; text = r["rewritten_text"]
            rows.append({
                "analysis_model_id": model_id, "analysis_model_label": label,
                "text_id": r["request_id"], "passage_id": r["passage_id"], "condition": r["condition"],
                "author_id": o["author_id"], "author_name": o["author_name"],
                "work_id": o["work_id"], "work_title": o["work_title"], "split": smap[r["passage_id"]],
                "qc_status": r["qc_status"], "qc_flags": r["qc_flags"], "text_sha256": sha_text(text), "text": text,
            })
    return rows


def build_feature_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    unique_originals = {r["passage_id"]: {"condition": "original", "text": r["text"]} for r in rows if r["condition"] == "original"}
    vocab = fh.select_char3_vocab(list(unique_originals.values()))
    id_cols = ["analysis_model_id","analysis_model_label","text_id","passage_id","condition","author_id","author_name","work_id","work_title","split","qc_status","qc_flags"]
    feature_rows: list[dict[str, Any]] = []
    feature_cols: list[str] | None = None
    for r in rows:
        feats = fh.base_features(r["text"], vocab)
        if feature_cols is None: feature_cols = list(feats.keys())
        out = {c: r[c] for c in id_cols}; out.update(feats); feature_rows.append(out)
    return feature_rows, feature_cols or []


def main() -> int:
    rows = build_master_rows(); feats, cols = build_feature_rows(rows)
    master_cols = ["analysis_model_id","analysis_model_label","text_id","passage_id","condition","author_id","author_name","work_id","work_title","split","qc_status","qc_flags","text_sha256","text"]
    id_cols = ["analysis_model_id","analysis_model_label","text_id","passage_id","condition","author_id","author_name","work_id","work_title","split","qc_status","qc_flags"]
    write_csv(MASTER_OUT, rows, master_cols)
    write_csv(FEATURES_OUT, feats, id_cols + cols)
    write_csv(FEATURE_REGISTRY, [{"feature": c, "feature_index": i+1, "feature_family": fh.feature_family(c)} for i,c in enumerate(cols)], ["feature","feature_index","feature_family"])
    split_rows = []
    for mid in MODELS:
        for split in SPLIT_COUNTS:
            sub = [r for r in rows if r["analysis_model_id"] == mid and r["split"] == split]
            split_rows.append({"analysis_model_id": mid, "split": split, "rows": len(sub), "unique_passages": len({r["passage_id"] for r in sub}), "authors": len({r["author_id"] for r in sub})})
    write_csv(SPLIT_SUMMARY, split_rows, ["analysis_model_id","split","rows","unique_passages","authors"])
    BUILD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    BUILD_REPORT.write_text(f"# E1 Groq Feature Build Report\n\n- master_rows: {len(rows)}\n- feature_rows: {len(feats)}\n- feature_columns: {len(cols)}\n", encoding="utf-8")
    print(f"Built E1 Groq features: rows={len(feats)}, features={len(cols)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
