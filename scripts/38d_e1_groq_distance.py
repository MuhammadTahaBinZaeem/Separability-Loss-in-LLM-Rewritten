"""E1 Groq distance-contraction downstream analysis."""
from __future__ import annotations
import csv, hashlib, math
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
FEAT=ROOT/'data/interim/e1_free_model_replication/groq_downstream/e1_groq_stylometric_features.csv'
REG=ROOT/'metadata/e1_groq_feature_registry.csv'
META=ROOT/'metadata'; LOGS=ROOT/'logs'
OUT=META/'e1_groq_distance_summary.csv'
REPORT=LOGS/'e1_groq_distance_analysis_report.md'
MANIFEST=META/'e1_groq_distance_manifest.csv'
MODELS=['groq_llama_3_3_70b_free','groq_qwen_32b_free','groq_gpt_oss_120b_free']
CONDS=['original','paraphrase','modernize','simplify']
SUBSETS=['all_rows','qc_pass_only']

def rc(p:Path)->list[dict[str,str]]:
    with p.open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def wc(p:Path,rows:list[dict[str,Any]],fields:list[str])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def keep(r:dict[str,str],s:str)->bool:return r['condition']=='original' or s=='all_rows' or r['qc_status']=='pass'
def mat(rows:list[dict[str,str]],cols:list[str])->list[list[float]]:return [[float(r[c]) for c in cols] for r in rows]
def mean_dist(rows:list[dict[str,str]],cols:list[str])->float:
    by=defaultdict(list)
    for r in rows:by[r['author_id']].append(r)
    cents={a:[sum(v)/len(v) for v in zip(*mat(rs,cols))] for a,rs in by.items() if rs}
    authors=sorted(cents); ds=[]
    for i,a in enumerate(authors):
        for b in authors[i+1:]:ds.append(math.sqrt(sum((x-y)**2 for x,y in zip(cents[a],cents[b]))))
    return round(sum(ds)/len(ds),6) if ds else 0.0

def main()->int:
    rows=rc(FEAT); cols=[r['feature'] for r in rc(REG)]
    families={'all_features':cols,'function_word':[c for c in cols if c.startswith('fw_')],'char3':[c for c in cols if c.startswith('char3_')],'punctuation':[c for c in cols if 'per_1000w' in c or c in {'quote_balance'}]}
    out=[]
    for mid in MODELS:
        mr=[r for r in rows if r['analysis_model_id']==mid]
        for sub in SUBSETS:
            sr=[r for r in mr if keep(r,sub)]
            for fam,fcols in families.items():
                orig_rows=[r for r in sr if r['condition']=='original']
                orig=mean_dist(orig_rows,fcols)
                for cond in CONDS:
                    cr=[r for r in sr if r['condition']==cond]
                    d=mean_dist(cr,fcols)
                    out.append({'analysis_model_id':mid,'sensitivity_subset':sub,'feature_family':fam,'condition':cond,'rows':len(cr),'authors':len({r['author_id'] for r in cr}),'mean_pairwise_centroid_distance':d,'original_distance':orig,'distance_ratio_vs_original':round(d/orig,6) if orig else 0.0})
    fields=['analysis_model_id','sensitivity_subset','feature_family','condition','rows','authors','mean_pairwise_centroid_distance','original_distance','distance_ratio_vs_original']
    wc(OUT,out,fields); wc(MANIFEST,[{'artifact':OUT.stem,'path':OUT.relative_to(ROOT).as_posix(),'size_bytes':OUT.stat().st_size,'sha256':sha(OUT)}],['artifact','path','size_bytes','sha256'])
    focus=[r for r in out if r['sensitivity_subset']=='all_rows' and r['feature_family']=='all_features']
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text('# E1 Groq Distance Analysis Report\n\n'+'\n'.join(f"- {r['analysis_model_id']} / {r['condition']}: rows={r['rows']}, distance_ratio={r['distance_ratio_vs_original']}" for r in focus)+'\n',encoding='utf-8')
    print(f'E1 Groq distance analysis rows: {len(out)}')
    return 0
if __name__=='__main__':raise SystemExit(main())
