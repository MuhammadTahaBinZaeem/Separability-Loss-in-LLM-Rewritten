"""Final checker for E1 Groq downstream analysis outputs."""
from __future__ import annotations
import csv, hashlib
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'metadata'; LOGS=ROOT/'logs'; DATA=ROOT/'data/interim/e1_free_model_replication/groq_downstream'
TRANSFER=META/'e1_groq_transfer_summary.csv'
SAME=META/'e1_groq_same_condition_summary.csv'
DIST=META/'e1_groq_distance_summary.csv'
FEATURES=DATA/'e1_groq_stylometric_features.csv'
MASTER=DATA/'e1_groq_master_text_dataset.csv'
SUMMARY=META/'e1_groq_downstream_completion_summary.csv'
REPORT=LOGS/'e1_groq_downstream_completion_report.md'
MANIFEST=META/'e1_groq_downstream_completion_manifest.csv'
MODELS=['groq_llama_3_3_70b_free','groq_qwen_32b_free','groq_gpt_oss_120b_free']
CONDS=['original','paraphrase','modernize','simplify']
REWRITE=['paraphrase','modernize','simplify']
SUBSETS=['all_rows','qc_pass_only']
SPLITS=['validation','test']
FAMILIES=['all_features','function_word','char3','punctuation']

def rc(p:Path)->list[dict[str,str]]:
    with p.open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def wc(p:Path,rows:list[dict[str,Any]],fields:list[str])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def ffloat(x:str)->float:
    try:return float(x)
    except Exception:return 0.0

def main()->int:
    errors=[]; lines=['# E1 Groq Downstream Completion Report','']
    required=[TRANSFER,SAME,DIST,FEATURES,MASTER]
    for p in required:
        if not p.exists(): errors.append(f'missing {p.relative_to(ROOT)}')
        elif p.stat().st_size<=0: errors.append(f'empty {p.relative_to(ROOT)}')
    if errors:
        REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text('\n'.join(lines+['## Errors','']+['- '+e for e in errors]),encoding='utf-8')
        print('FAIL: missing/empty downstream artifacts'); return 1
    transfer=rc(TRANSFER); same=rc(SAME); dist=rc(DIST); features=rc(FEATURES); master=rc(MASTER)
    if len(master)!=1440: errors.append(f'master rows expected 1440, found {len(master)}')
    if len(features)!=1440: errors.append(f'feature rows expected 1440, found {len(features)}')
    if len(transfer)!=len(MODELS)*len(SUBSETS)*len(SPLITS)*len(CONDS): errors.append(f'transfer rows expected 48, found {len(transfer)}')
    if len(same)!=len(MODELS)*len(SUBSETS)*len(SPLITS)*len(CONDS): errors.append(f'same-condition rows expected 48, found {len(same)}')
    if len(dist)!=len(MODELS)*len(SUBSETS)*len(FAMILIES)*len(CONDS): errors.append(f'distance rows expected 96, found {len(dist)}')
    transfer_keys={(r['analysis_model_id'],r['sensitivity_subset'],r['split'],r['condition']) for r in transfer}
    same_keys={(r['analysis_model_id'],r['sensitivity_subset'],r['split'],r['condition']) for r in same}
    dist_keys={(r['analysis_model_id'],r['sensitivity_subset'],r['feature_family'],r['condition']) for r in dist}
    for mid in MODELS:
        for sub in SUBSETS:
            for split in SPLITS:
                for cond in CONDS:
                    if (mid,sub,split,cond) not in transfer_keys: errors.append(f'missing transfer combo {mid}/{sub}/{split}/{cond}')
                    if (mid,sub,split,cond) not in same_keys: errors.append(f'missing same combo {mid}/{sub}/{split}/{cond}')
            for fam in FAMILIES:
                for cond in CONDS:
                    if (mid,sub,fam,cond) not in dist_keys: errors.append(f'missing distance combo {mid}/{sub}/{fam}/{cond}')
    summary=[]
    for mid in MODELS:
        tbase=[r for r in transfer if r['analysis_model_id']==mid and r['sensitivity_subset']=='all_rows' and r['split']=='test' and r['condition']=='original'][0]
        original_f1=ffloat(tbase['macro_f1'])
        for cond in REWRITE:
            t=[r for r in transfer if r['analysis_model_id']==mid and r['sensitivity_subset']=='all_rows' and r['split']=='test' and r['condition']==cond][0]
            s=[r for r in same if r['analysis_model_id']==mid and r['sensitivity_subset']=='all_rows' and r['split']=='test' and r['condition']==cond][0]
            d=[r for r in dist if r['analysis_model_id']==mid and r['sensitivity_subset']=='all_rows' and r['feature_family']=='all_features' and r['condition']==cond][0]
            fw=[r for r in dist if r['analysis_model_id']==mid and r['sensitivity_subset']=='all_rows' and r['feature_family']=='function_word' and r['condition']==cond][0]
            summary.append({'analysis_model_id':mid,'condition':cond,'original_test_macro_f1':original_f1,'transfer_test_macro_f1':t['macro_f1'],'transfer_macro_f1_loss':t['macro_f1_loss_vs_original'],'same_condition_survival':s['macro_f1_survival_vs_original'],'all_feature_distance_ratio':d['distance_ratio_vs_original'],'function_word_distance_ratio':fw['distance_ratio_vs_original']})
    wc(SUMMARY,summary,['analysis_model_id','condition','original_test_macro_f1','transfer_test_macro_f1','transfer_macro_f1_loss','same_condition_survival','all_feature_distance_ratio','function_word_distance_ratio'])
    artifacts=[TRANSFER,SAME,DIST,FEATURES,MASTER,SUMMARY]
    wc(MANIFEST,[{'artifact':p.stem,'path':p.relative_to(ROOT).as_posix(),'size_bytes':p.stat().st_size,'sha256':sha(p)} for p in artifacts],['artifact','path','size_bytes','sha256'])
    lines += ['## Validated artifacts','']+[f'- `{p.relative_to(ROOT)}`' for p in artifacts]
    lines += ['','## Main manuscript summary table','']
    for r in summary:
        lines.append(f"- {r['analysis_model_id']} / {r['condition']}: transfer_loss={r['transfer_macro_f1_loss']}, same_survival={r['same_condition_survival']}, all_distance_ratio={r['all_feature_distance_ratio']}, function_word_ratio={r['function_word_distance_ratio']}")
    if errors:
        lines += ['','## Errors','']+['- '+e for e in errors]
        REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print('FAIL: E1 Groq downstream checker found errors')
        for e in errors[:20]: print('- '+e)
        return 1
    lines += ['','## Final verdict','','PASS: E1 Groq downstream outputs are complete for the scoped free-model replication. Use as robustness evidence, not as a replacement for the frozen core experiment.']
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('PASS: E1 Groq downstream checker passed')
    return 0
if __name__=='__main__':raise SystemExit(main())
