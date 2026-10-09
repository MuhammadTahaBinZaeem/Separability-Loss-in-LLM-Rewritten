"""Reproduce manuscript figures and tables from frozen results; no model fitting."""
from pathlib import Path
import argparse
import ast
import csv
import io
import hashlib
import json
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--study-root',type=Path,default=HERE.parent,help='Repository root or fresh public replay study root')
args = parser.parse_args()
STUDY_ROOT=args.study_root.resolve()
BASE = STUDY_ROOT / 'revision/expanded_v3'
OUT = HERE / 'figures'
OUT.mkdir(exist_ok=True)
TABLES = HERE / 'tables'
TABLES.mkdir(exist_ok=True)
ARMS = ['gem31lite', 'azure_replication', 'codex51', 'luna56', 'terra56', 'astra_session']
LABELS = dict(zip(ARMS, ['Gemini 3.1 Flash Lite', 'GPT-5.4 Nano', 'GPT-5.1 Codex', 'GPT-5.6 Luna', 'GPT-5.6 Terra', 'Codex session (Astra label)']))
SHORT = dict(zip(ARMS, ['Gemini', 'Nano', 'Codex', 'Luna', 'Terra', 'Session']))
CONDITIONS = ['paraphrase', 'modernize', 'simplify']
COLORS = dict(zip(CONDITIONS, ['#0072B2', '#D55E00', '#009E73']))
INPUTS = {}

def read(path):
    path = Path(path)
    data = path.read_bytes()
    key=path.relative_to(STUDY_ROOT).as_posix() if path.is_relative_to(STUDY_ROOT) else 'companion/'+path.relative_to(HERE).as_posix()
    INPUTS[key] = hashlib.sha256(data).hexdigest()
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))

def readj(path):
    data = path.read_bytes()
    INPUTS[path.relative_to(BASE.parent.parent).as_posix()] = hashlib.sha256(data).hexdigest()
    return json.loads(data)

def write(name, rows):
    with (TABLES / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'axes.titlesize': 10, 'axes.labelsize': 9,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'savefig.facecolor': 'white'})

def save(fig, stem):
    for ext in ['png', 'pdf', 'svg']:
        fig.savefig(OUT / f'{stem}.{ext}', dpi=450, bbox_inches='tight', pad_inches=.12)
    plt.close(fig)

primary = read(BASE / 'primary_analysis/all_models_comparisons.csv')
assert len(primary) == 54
write('S1_primary_all_54.csv', primary)
sem = read(BASE / 'semantic_sensitivity/comparisons.csv')
assert len(sem) == 108
write('S2_semantic_all_108.csv', sem)
release = BASE / 'review_release/self_reported_875f34242015cc50'
rating_summary = read(release / 'rating_summary.csv')
write('S3_rating_summary.csv', rating_summary)
write('S4_dyad_agreement.csv', read(release / 'agreement.csv'))
originals = read(BASE / 'corpus/originals.csv')
registry = read(STUDY_ROOT / 'audit_tools/work_registry_current.csv')
write('S5_works.csv', [{**{k:r[k] for k in ['author_id','work_id','title','outer_fold']},'source_id':r['gutenberg_id'],'selected_count':r['selected_passages']} for r in registry])
availability, length, transfer, affine, panels, alphas, feature_counts, failures = [], [], [], [], [], [], [], []
transfer_contrasts, warning_sensitivity, ablations = [], [], []
for arm in ARMS:
    rows = read(BASE / f'generation/{arm}/rewrites.csv')
    counts = Counter(r['qc_status'] for r in rows)
    availability.append({'model_key':arm,'label':LABELS[arm],'requests':len(rows),
        'valid':sum(r['qc_status'] in ['pass','warning'] for r in rows),
        'warning':counts['warning'],'failed':sum(r['qc_status'] not in ['pass','warning'] for r in rows)})
    for r in rows:
        if r['qc_status'] not in ['pass','warning']:
            failures.append({'model_key':arm, **{k:r.get(k,'') for k in ['request_id','passage_id','condition','qc_status','qc_flags','finish_reason','outcome_type']}})
    for condition in CONDITIONS:
        valid = [r for r in rows if r['condition']==condition and r['qc_status'] in ['pass','warning']]
        ratios = [float(r['length_ratio']) for r in valid]
        length.append({'model_key':arm, 'condition':condition, 'valid':len(valid),
                       'median_length_ratio':float(np.median(ratios)),
                       'q25':float(np.quantile(ratios,.25)), 'q75':float(np.quantile(ratios,.75))})
    for r in read(BASE / f'extensions/jql_v1/{arm}/metrics.csv'):
        transfer.append({'model_key':arm, **r})
    for r in read(BASE / f'extensions/jql_v1/{arm}/contrasts.csv'):
        transfer_contrasts.append({'model_key':arm, **r})
    for r in read(BASE / f'primary_analysis/{arm}/warning_sensitivity.csv'):
        warning_sensitivity.append({'model_key':arm, **r})
    for r in read(BASE / f'primary_analysis/{arm}/metrics.csv'):
        ablations.append({'model_key':arm, **r})
    for r in readj(BASE / f'extensions/jql_v1/{arm}/panel_status.json'):
        panels.append({'model_key':arm, **{k:r[k] for k in ['panel','status','eligible_passages','minimum_words','crop_size']},'missing_works':json.dumps(r['missing_works'])})
    summ = read(BASE / f'extensions/jql_v1/{arm}/explanatory_model/summary.csv')
    cont = read(BASE / f'extensions/jql_v1/{arm}/explanatory_model/contrasts.csv')
    for r in cont:
        if r['contrast'] != 'affine_improvement':
            continue
        match = {s['mapping']:s for s in summ if all(s[k]==r[k] for k in ['panel','family','domain'])}
        t,a = float(match['translation']['mse']),float(match['scalar_affine']['mse'])
        affine.append({'model_key':arm, **r,'translation_mse':t, 'affine_mse':a,'relative_mse_reduction':(t-a)/t})
    p = BASE / f'extensions/jql_v1/{arm}/explanatory_model/parameters.jsonl'
    data = p.read_bytes()
    INPUTS[p.relative_to(BASE.parent.parent).as_posix()] = hashlib.sha256(data).hexdigest()
    for raw in data.decode('utf-8').splitlines():
        r = json.loads(raw)
        if r['mapping']=='scalar_affine':
            alphas.append({'model_key':arm, **{k:r[k] for k in ['panel','fold','family','domain','alpha']}, 'feature_count':len(r['feature_names'])})

for name, rows in [('S6_generation_availability.csv',availability),('S7_length_ratios.csv',length),
                   ('S8_transfer_all_panels.csv',transfer),('S9_affine_contrasts.csv',affine),
                   ('S10_length_panel_coverage.csv',panels),('S11_affine_parameters.csv',alphas),
                   ('S12_first_output_failures.csv',failures),
                   ('S13_transfer_contrasts.csv',transfer_contrasts),
                   ('S14_warning_sensitivity.csv',warning_sensitivity),
                   ('S15_primary_feature_panels.csv',ablations)]:
    write(name,rows)

# Fig. 1: full planned primary family, with marginal intervals and Holm markers.
classifiers = ['nearest_centroid','gaussian_nb','lda_ledoit_wolf_shrinkage']
fig, axs = plt.subplots(1,3,figsize=(10.2,7.5), sharex=True, sharey=True)
for ax, classifier, title in zip(axs,classifiers,['Nearest centroid','Gaussian naive Bayes','Shrinkage LDA']):
    for ai, arm in enumerate(ARMS):
        for ci, c in enumerate(CONDITIONS):
            r = next(r for r in primary if r['model_key']==arm and r['classifier']==classifier and r['condition']==c)
            y = ai*4+ci
            v,lo,hi=map(float,[r['macro_f1_loss'],r['loss_ci_low'],r['loss_ci_high']])
            ax.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='o',color=COLORS[c],ms=4,capsize=2,lw=1)
            if float(r['p_holm'])<.05:
                ax.text(hi+.012,y,'*',va='center',fontsize=13,fontweight='bold')
        if ai<5:
            ax.axhline(ai*4+3,color='#dddddd',lw=.6)
    ax.axvline(0,color='#777777',lw=.8,ls='--')
    ax.set_title(title,pad=12)
    ax.set_xlabel('Original − rewrite macro-F1')
    ax.set_yticks([i*4+1 for i in range(6)])
    ax.set_yticklabels([SHORT[a] for a in ARMS])
    ax.set_xlim(-.04,.65)
    ax.set_ylim(23,-1)
    ax.grid(axis='x',alpha=.15)
fig.legend(handles=[Line2D([0],[0],marker='o',color=COLORS[c],label=c.capitalize(),lw=1) for c in CONDITIONS],loc='lower center',ncol=3,frameon=False)
fig.subplots_adjust(wspace=.17,bottom=.11,left=.08,top=.94)
save(fig,'Figure_1_primary_losses')

# Fig. 2: same-cohort original-transfer/adapted comparison, no cross-arm rankings.
fig,axs=plt.subplots(1,3,figsize=(10.2,4.7),sharex=True,sharey=True)
for ax,c in zip(axs,CONDITIONS):
    for i,a in enumerate(ARMS):
        rows=[r for r in transfer if r['model_key']==a and r['panel']=='valid_full' and r['pipeline']=='shared_stylometry_nc']
        value=lambda train,test:float(next(r['macro_f1'] for r in rows if r['train_domain']==train and r['test_domain']==test))
        oo,orr,rr=value('original','original'),value('original',c),value(c,c)
        ax.plot([orr,rr],[i,i],color='#6e6e6e',lw=1.7)
        ax.plot(orr,i,'o',color='#D55E00',ms=5)
        ax.plot(rr,i,'s',color='#0072B2',ms=5)
        ax.plot(oo,i,'|',color='#202020',ms=13,mew=2)
    ax.set_title(c.capitalize(),pad=12)
    ax.set_xlabel('Macro-F1')
    ax.set_yticks(range(6),[SHORT[a] for a in ARMS])
    ax.set_xlim(.25,.75);ax.set_ylim(5.6,-.6);ax.grid(axis='x',alpha=.15)
fig.legend(handles=[Line2D([0],[0],marker='o',ls='',color='#D55E00',label='Original → rewrite'),Line2D([0],[0],marker='s',ls='',color='#0072B2',label='Rewrite → rewrite'),Line2D([0],[0],marker='|',ls='',color='#202020',markersize=10,label='Original → original')],loc='lower center',ncol=3,frameon=False)
fig.subplots_adjust(left=.09,wspace=.14,bottom=.18,top=.9)
save(fig,'Figure_2_transfer_recovery')

# Fig. 3: 36 paired held-out MSE reductions with marginal bootstrap intervals.
fig,axs=plt.subplots(1,2,figsize=(9.5,5.3),sharey=True)
for ax,fam,title in zip(axs,['all_features','function_words'],['All stylometric features','Function words only']):
    for ai,a in enumerate(ARMS):
        for ci,c in enumerate(CONDITIONS):
            r=next(r for r in affine if r['model_key']==a and r['panel']=='valid_full' and r['family']==fam and r['domain']==c)
            v,lo,hi=map(float,[r['mse_reduction'],r['ci_low'],r['ci_high']])
            ax.errorbar(v,ai+(ci-1)*.2,xerr=[[v-lo],[hi-v]],fmt='o',color=COLORS[c],capsize=2,ms=4,lw=1)
    ax.axvline(0,color='#777777',lw=.8,ls='--')
    ax.set_title(title,pad=12);ax.set_xlabel('Translation MSE − scalar-affine MSE')
    ax.set_yticks(range(6),[SHORT[a] for a in ARMS]);ax.set_ylim(5.6,-.6)
    ax.grid(axis='x',alpha=.15)
fig.legend(handles=[Line2D([0],[0],marker='o',color=COLORS[c],label=c.capitalize(),lw=1) for c in CONDITIONS],loc='lower center',ncol=3,frameon=False)
fig.subplots_adjust(left=.09,wspace=.22,bottom=.17,top=.92)
save(fig,'Figure_3_affine_prediction')

# Fig. 4: availability and rated semantic risk have explicit denominators.
fig,axs=plt.subplots(1,2,figsize=(9.5,4.7),sharey=True,gridspec_kw={'width_ratios':[1.25,1]})
for i,a in enumerate(ARMS):
    r=next(r for r in availability if r['model_key']==a)
    p=(r['valid']-r['warning'])/10.8;w=r['warning']/10.8;f=r['failed']/10.8
    axs[0].barh(i,p,color='#0072B2',height=.58)
    axs[0].barh(i,w,left=p,color='#E69F00',height=.58)
    axs[0].barh(i,f,left=p+w,color='#B44238',height=.58)
    s=next(s for s in rating_summary if s['model_key']==a)
    risk=int(s['risk_union_pairs']);v=100*risk/270
    axs[1].barh(i,v,color='#6A51A3',height=.58)
    axs[1].text(v+.6,i,f'{risk}/270 ({v:.1f}%)',va='center',fontsize=8)
for ax in axs:
    ax.set_yticks(range(6),[SHORT[a] for a in ARMS]);ax.set_ylim(5.6,-.6)
axs[0].set_xlim(0,100);axs[0].set_xlabel('Percentage of 1,080 first outcomes per arm')
axs[1].set_xlim(0,51);axs[1].set_xlabel('Percentage of 270 audited pairs per arm')
axs[0].set_title('A. Technical availability',pad=12)
axs[1].set_title('B. Either-rater semantic risk',pad=12)
from matplotlib.patches import Patch
fig.legend(handles=[Patch(color='#0072B2',label='Valid, no warning'),Patch(color='#E69F00',label='Valid, warning'),Patch(color='#B44238',label='Failed')],loc='lower center',ncol=3,frameon=False)
fig.subplots_adjust(left=.09,wspace=.22,bottom=.18,top=.9)
save(fig,'Figure_4_availability_semantics')

# Fig. 5: planned length controls, full common cohort and matched 200/300-word views.
fig,axs=plt.subplots(1,3,figsize=(10.2,6.5),sharex=True,sharey=True)
for ax,panel,title in zip(axs,['valid_full','w200_middle','w300_middle'],['Full valid texts','200-word middle windows','300-word middle windows']):
    for ai,a in enumerate(ARMS):
        for ci,c in enumerate(CONDITIONS):
            rows=[r for r in transfer if r['model_key']==a and r['panel']==panel and r['pipeline']=='shared_stylometry_nc']
            y=ai*4+ci
            if not rows:
                ax.text(.01,y,'Not estimable',fontsize=7,color='#777777',va='center')
                continue
            val=lambda train,test:float(next(r['macro_f1'] for r in rows if r['train_domain']==train and r['test_domain']==test))
            loss=val('original','original')-val('original',c)
            ax.plot(loss,y,'o',color=COLORS[c],ms=4)
        if ai<5:ax.axhline(ai*4+3,color='#dddddd',lw=.6)
    ax.axvline(0,color='#777777',lw=.8,ls='--');ax.set_title(title,pad=12)
    ax.set_xlabel('Original → original minus original → rewrite')
    ax.set_xlim(-.12,.45);ax.set_ylim(23,-1);ax.grid(axis='x',alpha=.15)
    ax.set_yticks([i*4+1 for i in range(6)],[SHORT[a] for a in ARMS])
fig.legend(handles=[Line2D([0],[0],marker='o',ls='',color=COLORS[c],label=c.capitalize()) for c in CONDITIONS],loc='lower center',ncol=3,frameon=False)
fig.subplots_adjust(left=.09,wspace=.17,bottom=.13,top=.93)
save(fig,'Figure_5_length_controls')

filtered=[r for r in sem if r['selection']=='audited_pairs_without_either_reviewer_risk']
fullaff=[r for r in affine if r['panel']=='valid_full']
facts={'availability':availability,'length':length,
       'primary_positive_losses':sum(float(r['macro_f1_loss'])>0 for r in primary),
       'primary_holm_significant':[r for r in primary if float(r['p_holm'])<.05],
       'semantic_filtered_positive':sum(float(r['macro_f1_loss'])>0 for r in filtered),
       'semantic_filtered_loss_range':[min(float(r['macro_f1_loss']) for r in filtered),max(float(r['macro_f1_loss']) for r in filtered)],
       'affine_full_comparisons':len(fullaff),
       'affine_relative_reduction_range':[min(r['relative_mse_reduction'] for r in fullaff),max(r['relative_mse_reduction'] for r in fullaff)],
       'rating_summary':rating_summary,'panels':panels,
       'returned_model_labels':{a:dict(Counter(r['returned_model'] for r in read(BASE/f'generation/{a}/rewrites.csv'))) for a in ARMS}}
(HERE/'facts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
prompt_source=STUDY_ROOT/'research_v2/generation.py'
INPUTS['research_v2/generation.py']=hashlib.sha256(prompt_source.read_bytes()).hexdigest()
prompts={}
for node in ast.parse(prompt_source.read_text(encoding='utf-8')).body:
    if isinstance(node,ast.Assign):
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id in ['SYSTEM','INSTRUCTIONS']:prompts[target.id]=ast.literal_eval(node.value)
(HERE/'generation_instructions.json').write_text(json.dumps(prompts,ensure_ascii=False,indent=2),encoding='utf-8')
manifest={'inputs':INPUTS,'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'outputs':{p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for d in [OUT,TABLES] for p in sorted(d.iterdir()) if p.is_file()},
          'source_results_modified':False,'plot_data_generated_from_existing_results':True}
(HERE/'figure_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'figures':5,'tables':15,'primary_tests':54,'filtered_semantic_comparisons':len(filtered),'failed_first_outputs':len(failures),'primary_holm_significant':len(facts['primary_holm_significant'])}))
