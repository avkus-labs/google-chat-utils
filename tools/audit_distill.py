"""Audit of *_distilled.md against *_human.md (turn coverage by anchors, code lines, secrets, fences).
Usage: python tools/audit_distill.py [output_data_dir] [out.csv]
Mechanical only: does not judge statuses or meaning."""
import sys,re,glob,os,json,csv
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.distillation import verifier as V, redactor as R, chunker as C
ANC=re.compile(r'\(ходы?\s+(\d+)(?:[–\-](\d+))?\)')
def rng(xs):
    out=[];
    for x in sorted(xs):
        if out and x==out[-1][1]+1: out[-1][1]=x
        else: out.append([x,x])
    return ",".join(f"{a}-{b}" if a!=b else str(a) for a,b in out)
def norm(s):
    s=s.replace('\r','').replace('…','...').replace('“','"').replace('”','"').replace('’',"'").replace('–','-').replace('—','-')
    return re.sub(r'[ \t]+',' ',s)
rows=[]
ROOT=sys.argv[1] if len(sys.argv)>1 else 'output_data'
OUT=sys.argv[2] if len(sys.argv)>2 else 'audit_distill.csv'
for d in sorted(glob.glob(os.path.join(ROOT,'*/'))):
    name=os.path.basename(d.rstrip('/\\'))
    hs=glob.glob(os.path.join(d, '*_human.md'))
    exact_dist=os.path.join(d, f'{name}_distilled.md')
    ds=[exact_dist] if os.path.exists(exact_dist) else glob.glob(os.path.join(d, '*_distilled.md'))
    r={'chat':name,'human':bool(hs),'distilled':len(ds)}
    if not hs or not ds: rows.append(r); continue
    h=open(hs[0],encoding='utf-8').read(); s=open(ds[0],encoding='utf-8').read()
    r['human_chars']=len(h)
    has_turns=bool(re.search(r'^### \*\*(User|Model)\*\*',h,re.M))
    r['has_SI']='### System Instruction' in h; r['turn_headers']=len(re.findall(r'^### \*\*(User|Model)\*\*',h,re.M)); r['user_turns']=len(re.findall(r'^### \*\*User\*\*',h,re.M))
    ok,fm=V.parse_frontmatter(s)
    m_fm=re.match(r"^---\r?\n.*?\r?\n---\r?\n",s,re.DOTALL); body=s[m_fm.end():] if m_fm else s
    g=fm.get('generated',{}) if isinstance(fm,dict) else {}
    r['model']=g.get('by',''); r['synth']=fm.get('synthesis_model','') if isinstance(fm,dict) else ''
    r['chunks']=fm.get('chunks'); r['v_status']=(fm.get('verification') or {}).get('status'); r['ratio']=(fm.get('verification') or {}).get('length_ratio')
    r['resolution']=fm.get('resolution','')
    r['desc_len']=len(str(fm.get('description',''))) ; r['dist_chars']=len(s)
    if not has_turns:
        r['kind']='NO_TURNS'; rows.append(r); continue
    t,si=C.extract_and_omit_system_instruction(h); t=C.remove_thoughts(t); t,n=C.number_turns(t); t,_=R.redact_secrets(t)
    r['turns']=n
    heads=[l for l in body.splitlines() if l.startswith('### ')]
    cov=set();ph=0;oor=0;noanc=0
    for l in heads:
        if re.match(r'### (Решения|Неудачные подходы|Сигнатуры ошибок|Уроки|Темы|Открытые вопросы|Ключевые|Основные)',l): continue
        m=ANC.search(l)
        if not m:
            noanc+=1; continue
        a=int(m.group(1));b=int(m.group(2) or a)
        if a<1 or b>n or a>b: oor+=1
        cov|=set(range(max(a,1),min(b,n)+1))
    miss=set(range(1,n+1))-cov
    r['blocks']=len(heads); r['cov_pct']=round(100*(n-len(miss))/n,1) if n else 0
    r['missing']=rng(miss) if miss else ''
    r['ph_anchor']=len(re.findall(r'N–N|\[не указан',body)); r['no_anchor']=noanc; r['oor']=oor
    ns=norm(t); tot=0;susp=0
    for m in V.CODE_BLOCK_RE.finditer(body):
        lines=[norm(l).strip() for l in m.group(1).splitlines() if l.strip()]
        if not lines: continue
        tot+=1
        miss_l=sum(1 for l in lines if l not in ns)
        if len(lines)>=2 and miss_l/len(lines)>0.30: susp+=1
    r['code']=tot; r['code_susp']=susp
    _,cnt=R.redact_secrets(s); r['secrets']=sum(cnt.values())
    r['conf']=body.count('[подтверждено]'); r['prop']=body.count('[предложено моделью]'); r['refut']=body.count('[опровергнуто]')
    r['nosig']=body.count('Без значимого содержания')
    r['prepared_chars']=len(t)
    rows.append(r)
keys=sorted({k for r in rows for k in r},key=lambda k:['chat','model','synth','chunks','turns','cov_pct','missing'].index(k) if k in ['chat','model','synth','chunks','turns','cov_pct','missing'] else 99)
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)
print(len(rows),'rows ->',OUT)
