"""E1 Groq transfer-only downstream analysis."""
from __future__ import annotations
import csv, importlib.util, hashlib
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
FEAT=ROOT/'data/interim/e1_free_model_replication/groq_downstream/e1_groq_stylometric_features.csv'
REG=ROOT/'metadata/e1_groq_feature_registry.csv'
META=ROOT/'metadata'; LOGS=ROOT/'logs'
OUT=META/'e1_groq_transfer_summary.csv'
REPORT=LOGS/'e1_groq_transfer_analysis_report.md'
MANIFEST=META/'e1_groq_transfer_manifest.csv'
MODELS=['groq_llama_3_3_70b_free','groq_qwen_32b_free','groq_gpt_oss_120b_free']
CONDS=['original','paraphrase','modernize','simplify']
SUBSETS=['all_rows','qc_pass_only']
SPLITS=['validation','test']

spec=importlib.util.spec_from_file_location('mh',ROOT/'scripts/16_run_original_to_rewritten_degradation.py')
mh=importlib.util.module_from_spec(spec); spec.loader.exec_module(mh)  # type: ignore[union-attr]

def rc(p:Path)->list[dict[str,str]]:
    with p.open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def wc(p:Path,rows:list[dict[str,Any]],fields:list[str])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def keep(r:dict[str,str],s:str)->bool:return r['condition']=='original' or s=='all_rows' or r['qc_status']=='pass'
def mat(rows:list[dict[str,str]],cols:list[str])->list[list[float]]:return [[float(r[c]) for c in cols] for r in rows]
def clf(train:list[dict[str,str]],ev:list[dict[str,str]],cols:list[str])->dict[str,float]:
    if not train or not ev or len({r['author_id'] for r in train})<6:return {'accuracy':0.0,'macro_f1':0.0,'weighted_f1':0.0}
    means,stds=mh.zscore_fit(mat(train,cols)); model=mh.fit_nearest_centroid(mh.zscore_apply(mat(train,cols),means,stds),[r['author_id'] for r in train])
    pred=mh.predict_nearest_centroid(model,mh.zscore_apply(mat(ev,cols),means,stds))
    return mh.evaluate([r['author_id'] for r in ev],pred)

def main()->int:
    rows=rc(FEAT); cols=[r['feature'] for r in rc(REG)]; out=[]
    for mid in MODELS:
        mr=[r for r in rows if r['analysis_model_id']==mid]
        for sub in SUBSETS:
            sr=[r for r in mr if keep(r,sub)]
            tr=[r for r in sr if r['split']=='train' and r['condition']=='original']
            for split in SPLITS:
                base=None; temp=[]
                for cond in CONDS:
                    ev=[r for r in sr if r['split']==split and r['condition']==cond]
                    m=clf(tr,ev,cols)
                    if cond=='original':base=m
                    temp.append({'analysis_model_id':mid,'sensitivity_subset':sub,'classifier':'nearest_centroid','split':split,'condition':cond,'rows':len(ev),'authors':len({r['author_id'] for r in ev}),**m})
                assert base is not None
                for r in temp:
                    r['accuracy_loss_vs_original']=round(float(base['accuracy'])-float(r['accuracy']),6)
                    r['macro_f1_loss_vs_original']=round(float(base['macro_f1'])-float(r['macro_f1']),6)
                    r['weighted_f1_loss_vs_original']=round(float(base['weighted_f1'])-float(r['weighted_f1']),6)
                    out.append(r)
    fields=['analysis_model_id','sensitivity_subset','classifier','split','condition','rows','authors','accuracy','macro_f1','weighted_f1','accuracy_loss_vs_original','macro_f1_loss_vs_original','weighted_f1_loss_vs_original']
    wc(OUT,out,fields); wc(MANIFEST,[{'artifact':OUT.stem,'path':OUT.relative_to(ROOT).as_posix(),'size_bytes':OUT.stat().st_size,'sha256':sha(OUT)}],['artifact','path','size_bytes','sha256'])
    focus=[r for r in out if r['sensitivity_subset']=='all_rows' and r['split']=='test']
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text('# E1 Groq Transfer Analysis Report\n\n'+'\n'.join(f"- {r['analysis_model_id']} / {r['condition']}: rows={r['rows']}, macro_f1={r['macro_f1']}, loss={r['macro_f1_loss_vs_original']}" for r in focus)+'\n',encoding='utf-8')
    print(f'E1 Groq transfer analysis rows: {len(out)}')
    return 0
if __name__=='__main__':raise SystemExit(main())
