"""Grouped out-of-fold attribution and distances rebuilt from source text."""
from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import NearestCentroid
from threadpoolctl import threadpool_limits

from .corpus import AUTHORS
from .features import FoldFeatures, feature_family
from .generation import consolidate, verify_corpus
from .inference import holm, paired_uncertainty
from .io import OUT, file_hash, read_csv, read_json, write_csv, write_json

CLASSIFIERS = ["nearest_centroid", "gaussian_nb", "lda_ledoit_wolf_shrinkage"]
FAMILIES = ["char3", "function_word", "length_rhythm", "punctuation", "lexical_richness", "register_marker"]
PRED_FIELDS = ["model_key","classifier","feature_set","fold","passage_id","author_id","work_id",
               "condition","predicted_author","qc_status"]


def classifier(name: str):
    if name == "nearest_centroid":
        return NearestCentroid(metric="euclidean", priors="uniform")
    if name == "gaussian_nb":
        return GaussianNB(var_smoothing=1e-9, priors=np.full(len(AUTHORS),1/len(AUTHORS)))
    if name == "lda_ledoit_wolf_shrinkage":
        return LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=np.full(len(AUTHORS),1/len(AUTHORS)))
    raise ValueError(name)


def split_rows(originals: list[dict], fold: int):
    train = [r for r in originals if int(r["outer_fold"]) != fold]
    test = [r for r in originals if int(r["outer_fold"]) == fold]
    train_groups = {(r["author_id"], r["work_id"]) for r in train}
    test_groups = {(r["author_id"], r["work_id"]) for r in test}
    if train_groups & test_groups:
        raise ValueError("A work crosses the train-test boundary")
    if {r["author_id"] for r in train} != set(AUTHORS) or {r["author_id"] for r in test} != set(AUTHORS):
        raise ValueError("Missing author in a fold")
    return train, test


def distance_rows(fold: int, model_key: str, features: FoldFeatures, conditions: dict[str, tuple[np.ndarray,list[dict]]]) -> list[dict]:
    result = []
    for family in ("function_word", "all_features"):
        mask = np.array([family == "all_features" or feature_family(n)==family for n in features.feature_names_])
        if not mask.any():
            continue
        centroids = {}
        for condition, (matrix, rows) in conditions.items():
            centroids[condition] = {author: matrix[[r["author_id"]==author for r in rows]][:,mask].mean(axis=0) for author in AUTHORS}
        base = centroids["original"]
        base_dist = float(np.mean([np.mean(np.abs(base[a]-base[b])) for a,b in combinations(AUTHORS,2)]))
        for condition, current in centroids.items():
            distances = [np.mean(np.abs(current[a]-current[b])) for a,b in combinations(AUTHORS,2)]
            distance = float(np.mean(distances))
            result.append({"model_key":model_key,"fold":fold,"feature_set":family,"condition":condition,
                           "mean_inter_author_delta":distance,"ratio_to_original":distance/base_dist if base_dist>0 else "",
                           "mean_original_to_rewrite_centroid_shift":float(np.mean([np.mean(np.abs(current[a]-base[a])) for a in AUTHORS])),
                           "reference_scaler":"original_training_only","inference":"descriptive_dependent_author_pairs"})
    return result


def run(bootstraps: int = 5000, permutations: int = 9999, ablations: bool = True) -> None:
    freeze = verify_corpus()
    originals = read_csv(OUT / "corpus/originals.csv")
    plan = read_json(OUT / "generation_plan.json")
    rewrites, model_status = {}, {}
    for key in plan["models"]:
        if not (OUT / f"generation/{key}/requests.jsonl").exists():
            model_status[key] = {"complete":False,"reason":"requests_not_prepared"}
            continue
        model_status[key] = consolidate(key)
        if model_status[key]["complete"]:
            rows = read_csv(OUT / f"generation/{key}/rewrites.csv")
            mapping = {(r["passage_id"],r["condition"]):r for r in rows}
            if len(mapping) != 3*len(originals):
                raise ValueError("Generation join is not one-to-one")
            for original in originals:
                for condition in plan["conditions"]:
                    row = mapping[(original["passage_id"],condition)]
                    if row["source_sha256"] != original["text_sha256"]:
                        raise ValueError("Rewrite paired with a different original")
            rewrites[key] = mapping
    predictions, distances = [], []
    feature_sets = [None] + (FAMILIES if ablations and rewrites else [])
    for omit in feature_sets:
        feature_set = "full" if omit is None else f"without_{omit}"
        for fold in sorted({int(r["outer_fold"]) for r in originals}):
            train, test = split_rows(originals,fold)
            features = FoldFeatures(omit_family=omit).fit([r["text"] for r in train],[r["passage_id"] for r in train])
            x_train, x_test = features.transform([r["text"] for r in train]), features.transform([r["text"] for r in test])
            write_json(OUT / f"results/folds/{feature_set}_{fold}.json",features.evidence())
            fitted = {name:classifier(name).fit(x_train,[r["author_id"] for r in train]) for name in CLASSIFIERS}
            for model_key in list(rewrites) or ["original_baseline_only"]:
                conditions = {"original":(x_test,test)}
                if model_key in rewrites:
                    for condition in plan["conditions"]:
                        rr = [{**original, **rewrites[model_key][(original["passage_id"],condition)]} for original in test]
                        conditions[condition] = (features.transform([r["rewritten_text"] for r in rr]),rr)
                for name,model in fitted.items():
                    for condition,(matrix,rows) in conditions.items():
                        predicted = model.predict(matrix)
                        for row,label in zip(rows,predicted):
                            predictions.append({"model_key":model_key,"classifier":name,"feature_set":feature_set,
                                "fold":fold,"passage_id":row["passage_id"],"author_id":row["author_id"],
                                "work_id":row["work_id"],"condition":condition,"predicted_author":str(label),
                                "qc_status":row.get("qc_status","source_verified")})
                if omit is None:
                    distances.extend(distance_rows(fold,model_key,features,conditions))
            print(f"Fitted {feature_set}, held-out-work fold {fold}; train={len(train)}, test={len(test)}",flush=True)
    write_csv(OUT / "results/predictions.csv",predictions,PRED_FIELDS)
    write_csv(OUT / "results/distances.csv",distances)
    groups = defaultdict(list)
    for row in predictions:
        groups[(row["model_key"],row["classifier"],row["feature_set"],row["condition"])].append(row)
    metrics, confusions, author_metrics, work_metrics = [],[],[],[]
    for (model_key,name,features,condition), rows in groups.items():
        base = {"model_key":model_key,"classifier":name,"feature_set":features,"condition":condition}
        for fold in ["pooled"] + sorted({r["fold"] for r in rows}):
            rr = rows if fold=="pooled" else [r for r in rows if r["fold"]==fold]
            y,p = [r["author_id"] for r in rr],[r["predicted_author"] for r in rr]
            metrics.append({**base,"fold":fold,"rows":len(rr),"macro_f1":float(f1_score(y,p,labels=AUTHORS,average="macro",zero_division=0)),"accuracy":float(accuracy_score(y,p))})
        if features != "full":
            continue
        matrix = confusion_matrix([r["author_id"] for r in rows],[r["predicted_author"] for r in rows],labels=AUTHORS)
        for i,author in enumerate(AUTHORS):
            support, predicted = int(matrix[i].sum()),int(matrix[:,i].sum())
            author_metrics.append({**base,"author_id":author,"support":support,"f1":2*int(matrix[i,i])/(support+predicted) if support+predicted else 0.0})
            for j,pred_author in enumerate(AUTHORS):
                confusions.append({**base,"true_author":author,"predicted_author":pred_author,"count":int(matrix[i,j])})
        for author,work in sorted({(r["author_id"],r["work_id"]) for r in rows}):
            wr = [r for r in rows if r["author_id"]==author and r["work_id"]==work]
            work_metrics.append({**base,"author_id":author,"work_id":work,"rows":len(wr),"correct_attribution_rate":sum(r["predicted_author"]==author for r in wr)/len(wr)})
    write_csv(OUT / "results/metrics.csv",metrics)
    write_csv(OUT / "results/confusions.csv",confusions)
    write_csv(OUT / "results/per_author.csv",author_metrics)
    write_csv(OUT / "results/per_work.csv",work_metrics)
    comparisons, sensitivities = [],[]
    for model_key in rewrites:
        for name in CLASSIFIERS:
            original = {r["passage_id"]:r for r in groups[(model_key,name,"full","original")]}
            for condition in plan["conditions"]:
                paired = [{"passage_id":r["passage_id"],"author_id":r["author_id"],"work_id":r["work_id"],
                           "original_prediction":original[r["passage_id"]]["predicted_author"],
                           "rewrite_prediction":r["predicted_author"],"qc_status":r["qc_status"]}
                          for r in groups[(model_key,name,"full",condition)]]
                comparison = {"model_key":model_key,"classifier":name,"condition":condition,
                              **paired_uncertainty(paired,bootstraps,permutations)}
                comparisons.append(comparison)
                clean = [r for r in paired if r["qc_status"]=="pass"]
                if {r["author_id"] for r in clean}==set(AUTHORS):
                    y=[r["author_id"] for r in clean]
                    sensitivities.append({"model_key":model_key,"classifier":name,"condition":condition,
                        "selection":"warning_free_paired","paired_rows":len(clean),"excluded_rows":len(paired)-len(clean),
                        "original_macro_f1":float(f1_score(y,[r["original_prediction"] for r in clean],labels=AUTHORS,average="macro",zero_division=0)),
                        "rewrite_macro_f1":float(f1_score(y,[r["rewrite_prediction"] for r in clean],labels=AUTHORS,average="macro",zero_division=0))})
                print(f"Computed work-aware inference: {model_key}/{name}/{condition}",flush=True)
    adjusted = holm([r["p_work_swap_two_sided"] for r in comparisons],family_size=len(plan["models"])*len(CLASSIFIERS)*3)
    for row,value in zip(comparisons,adjusted):
        row["p_holm"] = value
    if comparisons:
        write_csv(OUT / "results/primary_comparisons.csv",comparisons)
    if sensitivities:
        write_csv(OUT / "results/warning_sensitivity.csv",sensitivities)
    status = {"corpus_sha256":freeze["corpus_sha256"],"model_status":model_status,
              "analysis_complete":len(rewrites)==len(plan["models"]),"prediction_rows":len(predictions),
              "comparison_count":len(comparisons),"primary_classifier":"nearest_centroid",
              "primary_model":plan["primary_model"],"bootstraps":bootstraps,"permutations":permutations,
              "ablations_included":ablations and bool(rewrites),"predictions_sha256":file_hash(OUT / "results/predictions.csv")}
    write_json(OUT / "results/analysis_status.json",status)
    print(f"Analysis complete={status['analysis_complete']}; complete generated models={list(rewrites)}")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstraps",type=int,default=5000)
    parser.add_argument("--permutations",type=int,default=9999)
    parser.add_argument("--no-ablations",action="store_true")
    args=parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.bootstraps,args.permutations,not args.no_ablations)


if __name__=="__main__":
    main()
