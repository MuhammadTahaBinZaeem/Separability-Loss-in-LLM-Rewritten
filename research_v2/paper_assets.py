"""Build an explicitly labeled review draft and figures from verified v2 artifacts."""
from __future__ import annotations

import json
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analysis import analysis_fingerprint
from .io import OUT,file_hash,read_csv,read_json,write_json,write_text

FOLDER=OUT / "paper_assets"
MODELS={"gem31lite":"Gemini 3.1 Flash-Lite","azure_replication":"Azure GPT-5.4 nano"}
CLASSIFIERS={"nearest_centroid":"Nearest centroid","gaussian_nb":"Gaussian NB","lda_ledoit_wolf_shrinkage":"Shrinkage LDA"}
CONDITIONS=("paraphrase","modernize","simplify")


def number(value,decimals=3):
    return "not estimable" if value in {"",None} else f"{float(value):.{decimals}f}"


def table(headers,rows):
    escape=lambda x:str(x).replace("|","\\|").replace("\n"," ")
    return "\n".join(["| "+" | ".join(map(escape,headers))+" |","| "+" | ".join(["---"]*len(headers))+" |"]+
                     ["| "+" | ".join(map(escape,row))+" |" for row in rows])


def save_figure(fig,name):
    fig.savefig(FOLDER / f"{name}.svg",bbox_inches="tight",metadata={"Date":None,"Creator":"research_v2.paper_assets"})
    fig.savefig(FOLDER / f"{name}.png",dpi=180,bbox_inches="tight",metadata={"Software":"research_v2.paper_assets"})
    plt.close(fig)


def figures(comparisons):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.hashsalt":"separability-v2","axes.spines.top":False,"axes.spines.right":False})
    primary=[r for r in comparisons if r["classifier"]=="nearest_centroid"]
    primary.sort(key=lambda r:(list(MODELS).index(r["model_key"]),CONDITIONS.index(r["condition"])))
    fig,ax=plt.subplots(figsize=(8.4,4.4))
    for i,row in enumerate(primary):
        color="#155e75" if row["model_key"]=="gem31lite" else "#a34315"
        ax.hlines(i,float(row["loss_ci_low"]),float(row["loss_ci_high"]),color=color,lw=2)
        ax.scatter(float(row["macro_f1_loss"]),i,color=color,s=40,zorder=3)
    ax.axvline(0,color="#666666",ls="--",lw=1)
    ax.set_yticks(range(len(primary)),[f"{MODELS[r['model_key']]} / {r['condition']}\n(n={r['paired_passages']})" for r in primary])
    ax.invert_yaxis(); ax.set_xlabel("Paired macro-F1 loss (original minus rewrite)")
    ax.set_title("Nearest-centroid attribution, held-out works\n95% conditional paired work/passage bootstrap intervals",loc="left",fontsize=11)
    ax.grid(axis="x",alpha=.18); fig.tight_layout(); save_figure(fig,"figure_1_paired_loss")
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    for ax,(model,label) in zip(axes,MODELS.items()):
        rows=read_csv(OUT / f"generation/{model}/rewrites.csv")
        for condition,color in zip(CONDITIONS,("#155e75","#a34315","#527548")):
            ratios=np.sort([float(r["length_ratio"]) for r in rows if r["condition"]==condition and r["qc_status"]!="fail"])
            if ratios.size:
                ax.plot(ratios,np.arange(1,len(ratios)+1)/len(ratios),label=condition,color=color,lw=1.8)
        ax.axvspan(.85,1.15,color="#bbbbbb",alpha=.25)
        ax.axvline(1,color="#555555",lw=.8,ls="--")
        ax.set_title(label,fontsize=11); ax.set_xlabel("Rewrite/original word-count ratio"); ax.grid(alpha=.15)
    axes[0].set_ylabel("Cumulative fraction of technically valid outputs")
    axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle("Length compliance: shaded band is the requested ±15%",fontsize=12)
    fig.tight_layout(); save_figure(fig,"figure_2_length_compliance")


def run() -> dict:
    FOLDER.mkdir(parents=True,exist_ok=True)
    replacements={}
    from .source_review import validate as validate_source_review
    source_review=validate_source_review()
    replacements["SOURCE_REVIEW_STATUS"]=(f"A registered human source audit covers {source_review['reviewed']} passages with no unresolved correction flags. This is a human attestation linked to the frozen corpus, not a guarantee against every attribution ambiguity."
        if source_review.get("passed") else "A separate human source audit of all 360 passages has not yet passed the release gate. The issued packet requires a dated original verdict and note for every passage; no automated source match is substituted for this review.")
    registry=read_csv(OUT / "corpus/work_registry.csv")
    replacements["CORPUS_TABLE"]="Table 1. Frozen corpus; each work contributes twenty passages. Fold IDs are zero-based.\n\n"+table(
        ["Author","Work","Gutenberg ID","Held-out fold"],[[r["author_id"].title(),r["title"],r["source_id"],r["outer_fold"]] for r in registry])
    path=OUT / "results/analysis_status.json"
    status=read_json(path) if path.exists() else {}
    complete=status.get("analysis_complete",False) and status.get("analysis_fingerprint")==analysis_fingerprint()
    diagnostic=False
    if complete:
        from .release import analysis_checks
        analysis_checks()
    pending="Pending complete, current-code analysis of both generation ledgers. No historical result is inserted in this section."
    if not complete and status.get("comparison_count",0) and status.get("analysis_fingerprint")==analysis_fingerprint():
        from .release import analysis_checks
        report=analysis_checks(allow_partial=True)
        comparisons=read_csv(OUT / "results/primary_comparisons.csv")
        diagnostic=True
        interim="# Interim completed-model results — not the final two-model study\n\n"
        interim+="This companion reports only completed generation ledgers and validated current-code analysis. The main manuscript remains pending. Missing requests are not imputed or replaced. Human semantic and source reviews remain outstanding.\n\n"
        interim+="Models included: "+", ".join(MODELS[m] for m in report["models_included"])+".\n\n"
        interim+="Table 1. Paired attribution loss conditional on technically valid outputs, with all length warnings retained. Intervals use 5,000 paired hierarchical bootstrap replicates and condition on the fitted classifiers. Work-swap p-values use 9,999 draws. Interim Holm adjustment retains the full planned family of eighteen tests, with unavailable tests effectively assigned p=1; adjusted values must be recomputed when all eighteen are available.\n\n"
        interim+=table(["Classifier","Instruction","Pairs","Original F1","Rewrite F1","Loss [95% CI]","Interim Holm p"],
            [[CLASSIFIERS[r["classifier"]],r["condition"],r["paired_passages"],number(r["original_macro_f1"]),number(r["rewrite_macro_f1"]),
             f"{number(r['macro_f1_loss'])} [{number(r['loss_ci_low'])}, {number(r['loss_ci_high'])}]",number(r["p_holm"],4)] for r in comparisons])
        interim+="\n\nA positive loss indicates poorer transfer of an original-trained classifier. Bootstrap intervals and the work-swap test answer different conditional questions; an interval excluding zero is not a multiplicity-corrected significance claim. No pure-style, causal, or population-wide effect is identified.\n\n"
        primary=[r for r in comparisons if r["classifier"]=="nearest_centroid"]
        interim+=f"Nearest-centroid loss is positive in {sum(float(r['macro_f1_loss'])>0 for r in primary)} of {len(primary)} available comparisons; {sum(float(r['p_holm'])<.05 for r in primary)} cross .05 under the interim eighteen-test Holm adjustment. These are interim outcomes, not a completed two-model study.\n\n"
        qc=read_csv(OUT / "results/generation_summary.csv")
        for model in report["models_included"]:
            rows=[r for r in qc if r["model_key"]==model]
            total=lambda field:sum(int(r[field]) for r in rows)
            interim+=f"{MODELS[model]} has {total('accounted'):,} accounted requests: {total('native_responses'):,} native responses and {total('terminal_http_failures')} evidenced HTTP refusals; {total('valid')} outputs are technically valid and {total('failed')} fail technical QC or are refusals. "
        interim+="Failed outcomes are excluded only under the disclosed valid-output estimand. No failed output is rerolled.\n"
        write_text(FOLDER / "INTERIM_COMPLETED_MODEL_RESULTS.md",interim)
        pending="The full two-model analysis is pending. Appendix A reports the separately validated, interim Azure results."
    for field in ("RESULTS_ABSTRACT","GENERATION_RESULTS","ATTRIBUTION_RESULTS","ROBUSTNESS_RESULTS","DISTANCE_RESULTS","DISCUSSION_RESULTS","CONCLUSION_RESULTS"):
        replacements[field]=pending
    replacements["DRAFT_STATUS"]="> REVIEW DRAFT — NOT READY FOR SUBMISSION. Computational results, independent human review and archival status are distinguished below. This file is generated from `manuscript_v2_template.md`; edit that source, not the generated copy."
    if complete:
        if (FOLDER / "INTERIM_COMPLETED_MODEL_RESULTS.md").exists():
            write_text(FOLDER / "INTERIM_COMPLETED_MODEL_RESULTS.md","# Superseded interim companion\n\nThe current main manuscript now contains the complete-accounting two-model computational results. Use it and its evidence manifest; earlier interim multiplicity values must not be mixed with the final family.\n")
        comparisons=read_csv(OUT / "results/primary_comparisons.csv")
        primary=[r for r in comparisons if r["classifier"]=="nearest_centroid"]
        qc=read_csv(OUT / "results/generation_summary.csv")
        total_valid=sum(int(r["valid"]) for r in qc); total_failed=sum(int(r["failed"]) for r in qc)
        replacements["RESULTS_ABSTRACT"]=f"Complete request accounting yielded {total_valid:,} technically valid outputs and {total_failed} failed outcomes. "
        replacements["RESULTS_ABSTRACT"]+=" ".join(f"For {MODELS[m]}, nearest-centroid F1 losses were "+", ".join(
            f"{c}: {number(next(r['macro_f1_loss'] for r in primary if r['model_key']==m and r['condition']==c))}" for c in CONDITIONS)+"." for m in MODELS)
        replacements["GENERATION_RESULTS"]="Table 2. Each row has 360 assigned requests. Warnings are retained; failed outcomes are excluded from paired attribution. Accounted includes evidenced terminal HTTP refusals, not only native responses.\n\n"+table(
            ["Service","Instruction","Accounted","Valid","Warnings","Failed","Median length ratio"],
            [[MODELS[r["model_key"]],r["condition"],r["accounted"],r["valid"],r["warning"],r["failed"],number(r["median_length_ratio"])] for r in qc])
        replacements["GENERATION_RESULTS"]+="\n\nFailure-by-work and author details are retained in `revision/results/generation_cells.csv` and `generation_failures.csv`. Figure 2 displays length ratios among technically valid outputs.\n\n![Length compliance](figure_2_length_compliance.png)"
        replacements["ATTRIBUTION_RESULTS"]="Table 3. Primary nearest-centroid comparisons, matched on valid-output passage IDs. CI denotes the 95% paired hierarchical bootstrap interval. Holm p-values use all eighteen planned comparisons.\n\n"+table(
            ["Service","Instruction","Pairs","Original F1","Rewrite F1","Loss [95% CI]","Holm p"],
            [[MODELS[r["model_key"]],r["condition"],r["paired_passages"],number(r["original_macro_f1"]),number(r["rewrite_macro_f1"]),
              f"{number(r['macro_f1_loss'])} [{number(r['loss_ci_low'])}, {number(r['loss_ci_high'])}]",number(r["p_holm"],4)] for r in primary])
        replacements["ATTRIBUTION_RESULTS"]+="\n\nThe original F1 can differ between rows because each comparison uses its own identical surviving passage subset.\n\n![Paired attribution loss](figure_1_paired_loss.png)"
        replacements["ROBUSTNESS_RESULTS"]="Table 4. Fixed classifier robustness; effects are conditional on valid output, not independent experiments.\n\n"+table(
            ["Service","Classifier","Instruction","Loss","Holm p"],[[MODELS[r["model_key"]],CLASSIFIERS[r["classifier"]],r["condition"],number(r["macro_f1_loss"]),number(r["p_holm"],4)]
            for r in comparisons if r["classifier"]!="nearest_centroid"])
        sensitivity=read_csv(OUT / "results/warning_sensitivity.csv")
        unavailable=[r for r in sensitivity if r["all_authors_present"]!="True"]
        replacements["ROBUSTNESS_RESULTS"]+=f"\n\nWarning-free sensitivities retain paired originals and all six labels; {len(unavailable)} of {len(sensitivity)} comparisons lack full author coverage and are reported as not estimable. Their sample sizes are retained in `warning_sensitivity.csv`. All six leave-family-out predictions and pooled/fold metrics are available in `predictions.csv` and `metrics.csv`; they are descriptive rather than additional corrected hypothesis tests."
        metrics=read_csv(OUT / "results/metrics.csv")
        ablation=[]
        for model in MODELS:
            for condition in CONDITIONS:
                for feature in sorted({r["feature_set"] for r in metrics if r["feature_set"]!="full"}):
                    # Pooled metric denominators differ after failures; derive paired ablation loss from predictions below.
                    ablation.append((model,condition,feature))
        predictions=read_csv(OUT / "results/predictions.csv")
        from sklearn.metrics import f1_score
        from .corpus import AUTHORS
        by_group=defaultdict(list)
        for r in predictions:
            if r["classifier"]=="nearest_centroid":
                by_group[(r["model_key"],r["feature_set"],r["condition"])].append(r)
        ablation_rows=[]
        for model,condition,feature in ablation:
            original={r["passage_id"]:r for r in by_group[(model,feature,"original")]}
            rewritten=by_group[(model,feature,condition)]
            y=[r["author_id"] for r in rewritten]
            loss=f1_score(y,[original[r["passage_id"]]["predicted_author"] for r in rewritten],labels=AUTHORS,average="macro",zero_division=0)-f1_score(y,[r["predicted_author"] for r in rewritten],labels=AUTHORS,average="macro",zero_division=0)
            ablation_rows.append([MODELS[model],condition,feature,number(loss)])
        write_text(FOLDER / "feature_ablation_table.md",table(["Service","Instruction","Omitted family","Paired F1 loss"],ablation_rows)+"\n")
        replacements["ROBUSTNESS_RESULTS"]+=" See the [complete nearest-centroid ablation table](feature_ablation_table.md)."
        distances=read_csv(OUT / "results/distances.csv")
        replacements["DISTANCE_RESULTS"]="Table 5. Range across the three held-out-work folds of rewrite/original inter-author distance ratios. Values below one indicate smaller centroid separation in this representation. No author-pair independence test is applied.\n\n"+table(
            ["Service","Instruction","Feature set","Fold ratio range"],[[MODELS[m],c,f,f"{min(values):.3f}–{max(values):.3f}"]
              for m in MODELS for c in CONDITIONS for f in ("function_word","all_features")
              if (values:=[float(r["ratio_to_original"]) for r in distances if r["model_key"]==m and r["condition"]==c and r["feature_set"]==f and r["ratio_to_original"]!=""])])
        positives=sum(float(r["macro_f1_loss"])>0 for r in primary)
        significant=sum(float(r["p_holm"])<.05 for r in primary)
        replacements["DISCUSSION_RESULTS"]=f"The nearest-centroid point estimates show positive attribution loss in {positives} of six service/instruction comparisons; {significant} of six have Holm-adjusted p-values below .05 in the eighteen-comparison family. These counts summarize direction and conditional test outcomes, not the size, literary significance or semantic cause of each change; Table 3 supplies those numerical effects and intervals."
        replacements["CONCLUSION_RESULTS"]="The completed computational experiment yields the service- and instruction-specific paired effects reported above. Conclusions about faithful preservation of meaning remain conditional on the independent audit, and conclusions about literary homogenization remain narrower than a universal loss-of-style claim."
        figures(comparisons)
    from .annotations import validate as validate_annotations
    human=validate_annotations() if (OUT / "annotations/issued_manifest.json").exists() else {"complete":False}
    replacements["HUMAN_RESULTS"]="Two independent human reviews have not yet been verified. No agreement coefficient, preservation percentage or human-clean sensitivity result is asserted. The planned forms require 540 paired judgments from each reviewer. This unresolved validation limits interpretation and blocks submission readiness."
    if human.get("complete"):
        agreement=read_csv(OUT / "annotations/agreement.csv")
        replacements["HUMAN_RESULTS"]="Registered independent-review results:\n\n"+table(["Service","Field","Pairs","Raw agreement","Kappa"],
            [[MODELS[r["model_key"]],r["field"],r["items"],number(r["raw_agreement"]),r["kappa"]] for r in agreement])+"\n\nSee `semantic_sensitivity.csv` for the audited paired subset, and preserve disagreements separately. Reviewer identity and independence are attested, not inferred from text."
        summary=read_csv(OUT / "annotations/semantic_summary.csv")
        replacements["HUMAN_RESULTS"]+="\n\nPreservation risks apply only to the audited valid-output subset:\n\n"+table(
            ["Service","Instruction","Audited pairs","Either-reviewer risk","Risk fraction"],
            [[MODELS[r["model_key"]],r["condition"],r["audited_pairs"],r["risk_union"],number(r["risk_union_fraction"])] for r in summary])
    readiness_path=OUT / "readiness.json"
    readiness=read_json(readiness_path) if readiness_path.exists() else {}
    archive=readiness.get("checks",{}).get("published_archive",{})
    replacements["ARCHIVE_STATUS"]=f"The checksum-verified published archive is {archive['record_url']} (DOI {archive['doi']})." if archive.get("passed") else "No published, checksum-verified archival DOI is available yet. A token or reserved DOI is not represented as publication."
    template=(OUT / "manuscript_v2_template.md").read_text(encoding="utf-8")
    expected=set(re.findall(r"\{\{([A-Z_]+)\}\}",template))
    if expected!=set(replacements):
        raise ValueError("Manuscript fields changed without matching evidence bindings")
    draft=re.sub(r"\{\{([A-Z_]+)\}\}",lambda m:replacements[m[1]],template)
    if diagnostic:
        draft+="\n\n## Appendix A. Interim completed-model results\n\n"+interim.split("\n",1)[1].strip().replace("Table 1.","Table A1.")+"\n"
    write_text(FOLDER / "manuscript_REVIEW_DRAFT.md",draft)
    manifest={"computational_results_included":bool(complete),"independent_human_reviews_verified":bool(human.get("complete")),
              "interim_companion_included":diagnostic,
              "full_two_model_results_included":bool(complete),
              "submission_ready":False,"analysis_fingerprint":status.get("analysis_fingerprint",""),
              "template_sha256":file_hash(OUT / "manuscript_v2_template.md"),
              "artifact_sha256":{p.name:file_hash(p) for p in sorted(FOLDER.iterdir()) if p.is_file() and p.name!="manifest.json"}}
    write_json(FOLDER / "manifest.json",manifest)
    print(json.dumps(manifest,indent=2))
    return manifest


if __name__=="__main__":
    run()
