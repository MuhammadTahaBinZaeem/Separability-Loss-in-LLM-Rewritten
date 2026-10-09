"""Training-only vocabulary selection and scaling for interpretable stylometry."""
from __future__ import annotations

import importlib.util
import re
from collections import Counter
from functools import lru_cache

import numpy as np
from sklearn.preprocessing import StandardScaler

from .corpus import clean_text
from .io import ROOT, digest_text

# Reuse the text-local 85-feature definitions; never call the legacy main() or
# its full-corpus vocabulary selector.
_spec = importlib.util.spec_from_file_location("legacy_text_local_features", ROOT / "scripts/13_extract_stylometric_features.py")
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
FUNCTION_WORDS = _legacy.FUNCTION_WORDS


@lru_cache(maxsize=10000)
def local_features(text: str) -> tuple[dict, Counter]:
    canonical = clean_text(text)
    return _legacy.base_features(canonical, []), _legacy.char3s(canonical)


class FoldFeatures:
    def __init__(self, char_limit: int = 120, omit_family: str | None = None):
        self.char_limit = char_limit
        self.omit_family = omit_family

    def fit(self, texts: list[str], training_ids: list[str]) -> "FoldFeatures":
        if len(texts) != len(training_ids) or not texts:
            raise ValueError("Nonempty training texts must have matching IDs")
        counts = Counter()
        for text in texts:
            counts.update(local_features(text)[1])
        eligible = [g for g in counts if g.strip() and re.fullmatch(r"[a-z ,.;:'\"!?-]{3}", g)]
        self.vocabulary_ = sorted(eligible, key=lambda g: (-counts[g], g))[:self.char_limit]
        self.base_names_ = list(local_features(texts[0])[0])
        self.feature_names_all_ = self.base_names_ + [f"char3::{g}" for g in self.vocabulary_]
        matrix = self.raw_transform(texts)
        self.keep_ = np.var(matrix, axis=0) > 1e-12
        if self.omit_family:
            self.keep_ &= np.array([feature_family(n) != self.omit_family for n in self.feature_names_all_])
        if not self.keep_.any():
            raise ValueError("All training features constant/excluded")
        self.feature_names_ = [n for n, k in zip(self.feature_names_all_, self.keep_) if k]
        self.scaler_ = StandardScaler().fit(matrix[:, self.keep_])
        self.training_ids_ = list(training_ids)
        self.training_text_hashes_ = [digest_text(t) for t in texts]
        return self

    def raw_transform(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            fixed, char_counts = local_features(text)
            total = max(sum(char_counts.values()), 1)
            rows.append([fixed[n] for n in self.base_names_] + [1000 * char_counts[g] / total for g in self.vocabulary_])
        return np.asarray(rows, dtype=float)

    def transform(self, texts: list[str]) -> np.ndarray:
        return self.scaler_.transform(self.raw_transform(texts)[:, self.keep_])

    def evidence(self) -> dict:
        return {"training_ids": self.training_ids_, "training_text_hashes": self.training_text_hashes_,
                "char_trigrams": self.vocabulary_, "all_feature_names": self.feature_names_all_,
                "retained_feature_names": self.feature_names_, "retained_mask": self.keep_.tolist(),
                "mean": self.scaler_.mean_.tolist(), "scale": self.scaler_.scale_.tolist(),
                "sample_count": int(self.scaler_.n_samples_seen_), "omit_family": self.omit_family}


def feature_family(name: str) -> str:
    if name.startswith("char3::"):
        return "char3"
    return _legacy.feature_family(name)
