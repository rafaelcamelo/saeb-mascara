# -*- coding: utf-8 -*-
"""
Recuperação do código INEP (CO_ENTIDADE) das escolas mascaradas do Saeb (edições 2021 em diante)
Etapas: 5º ano EF, 9º ano EF e Ensino Médio — script reprodutível

Uso:  python3 recuperar_id_saeb.py <pasta_dados> <ano> <pasta_saida>

<pasta_dados> é varrida em busca dos arquivos do ano pedido (nomes como o Inep publica):
  TS_ESCOLA.csv e TS_ALUNO_{5EF,9EF,34EM}.csv do Saeb <ano> (em uma pasta com "saeb" e "<ano>" no caminho),
  microdados_ed_basica_<ano>.csv (Censo Escolar), AFD_ESCOLAS_<ano>*.xlsx, INSE_<ano>_escolas.xlsx e as
  planilhas de divulgação do Ideb por escola (divulgacao_anos_iniciais/anos_finais/ensino_medio_escolas_*.xlsx)
  de qualquer edição que traga as notas Saeb do <ano> (colunas VL_NOTA_MATEMATICA_<ano>).

Unidade: escola do TS_ESCOLA (ID_ESCOLA mascarado). Camadas:
  A) UF + médias LP/MT (2 casas) de cada etapa do TS_ESCOLA x notas Saeb <ano> das divulgações do Ideb
     (anos iniciais -> 5EF, anos finais -> 9EF, ensino médio -> EM). Só pares 1:1 dentro da etapa;
     as três etapas são unidas e qualquer conflito de código entre etapas é reportado.
  B) Escolas restantes: chaves obrigatórias UF + localização + % adequação docente (AFD) de AI, AF e EM
     (ausência também é informação); restrição de coerência do município mascarado (mapa máscara->IBGE
     aprendido nas camadas anteriores, atualizado iterativamente). Desempate por capital/interior,
     classificação Inse e matrículas (Censo): por série quando o Censo do ano as traz (2023);
     senão (2021), aproximação pela matrícula da etapa (AI/5, AF/4, EM/3), só como distância.
     Aceita só vencedor com folga >= 0,5 ponto nos dois sentidos (1:1).
  C) Resíduo: impressão digital do Inse (distribuição ponderada dos alunos pelos 8 níveis, recalculada
     dos microdados de aluno) com casamento único na UF, aceita só se o código também estiver entre os
     candidatos com UF + município + localização + AFD idênticos.
  Validação: a mesma impressão digital é comparada a PC_NIVEL_1..8 do arquivo Inse (tolerância 0,011 p.p.)
     para todos os pares das camadas A e B.
"""
import sys, os, glob, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

BASE = sys.argv[1] if len(sys.argv) > 1 else '.'
ANO = str(sys.argv[2]) if len(sys.argv) > 2 else '2023'
OUT = sys.argv[3] if len(sys.argv) > 3 else '.'
num = lambda s: pd.to_numeric(s, errors='coerce')
r1 = lambda s: s.round(1).fillna(-1)
UF = {'RO':11,'AC':12,'AM':13,'RR':14,'PA':15,'AP':16,'TO':17,'MA':21,'PI':22,'CE':23,'RN':24,'PB':25,'PE':26,
      'AL':27,'SE':28,'BA':29,'MG':31,'ES':32,'RJ':33,'SP':35,'PR':41,'SC':42,'RS':43,'MS':50,'MT':51,'GO':52,'DF':53}
MAT34 = ['QT_MAT_MED_PROP_3','QT_MAT_MED_PROP_4','QT_MAT_MED_CT_3','QT_MAT_MED_CT_4','QT_MAT_MED_NM_3','QT_MAT_MED_NM_4']
ETAPAS = {'5EF': 'divulgacao_anos_iniciais_escolas_', '9EF': 'divulgacao_anos_finais_escolas_',
          'EM': 'divulgacao_ensino_medio_escolas_'}

def achar(padrao, filtro=None, obrigatorio=True):
    ach = sorted(glob.glob(os.path.join(BASE, '**', padrao), recursive=True))
    if filtro: ach = [f for f in ach if filtro(f.lower())]
    if not ach and obrigatorio: sys.exit(f'arquivo não encontrado: {padrao} (ano {ANO}) em {BASE}')
    return ach

eh_saeb_do_ano = lambda f: 'saeb' in f and ANO in f
TS_ESCOLA = achar('TS_ESCOLA.csv', eh_saeb_do_ano)[0]
SAEB = os.path.dirname(TS_ESCOLA)
print('Saeb', ANO, '->', SAEB)

# ---------------- leitura ----------------
print('lendo TS_ESCOLA...')
ts = pd.read_csv(TS_ESCOLA, sep=';', encoding='latin1', low_memory=False)

def ler_divulgacao(prefixo):
    for f in sorted(achar(prefixo + '*.xlsx'), reverse=True):
        raw = pd.read_excel(f, header=None, nrows=15)
        hr = raw.index[raw.apply(lambda r: r.astype(str).eq('ID_ESCOLA').any(), axis=1)][0]
        cab = pd.read_excel(f, header=hr, nrows=0).columns
        if f'VL_NOTA_MATEMATICA_{ANO}' not in cab: continue
        print('   divulgação:', os.path.basename(f))
        d = pd.read_excel(f, header=hr, dtype=str)
        d = d[d.ID_ESCOLA.str.match(r'^\d+$', na=False)].copy()
        d['CO_UF'] = d.SG_UF.map(UF); d['CO_ENTIDADE'] = d.ID_ESCOLA.astype(int)
        d['mt'] = num(d[f'VL_NOTA_MATEMATICA_{ANO}']); d['lp'] = num(d[f'VL_NOTA_PORTUGUES_{ANO}'])
        return d.dropna(subset=['mt', 'lp'])[['CO_UF', 'mt', 'lp', 'CO_ENTIDADE']]
    sys.exit(f'nenhuma divulgação {prefixo}*.xlsx traz as notas de {ANO}')

print(f'lendo Censo {ANO}...')
fcenso = achar(f'microdados_ed_basica_{ANO}.csv')[0]
cab = pd.read_csv(fcenso, sep=';', encoding='latin1', nrows=0).columns
POR_SERIE = 'QT_MAT_FUND_AI_5' in cab
base_cols = ['CO_UF','CO_MUNICIPIO','NO_ENTIDADE','CO_ENTIDADE','TP_DEPENDENCIA','TP_LOCALIZACAO','TP_SITUACAO_FUNCIONAMENTO']
extra = (['QT_MAT_FUND_AI_5','QT_MAT_FUND_AF_9'] + MAT34) if POR_SERIE else ['QT_MAT_FUND_AI','QT_MAT_FUND_AF','QT_MAT_MED']
c = pd.read_csv(fcenso, sep=';', encoding='latin1', usecols=base_cols + extra, low_memory=False)
if POR_SERIE:
    c['m5'] = c.QT_MAT_FUND_AI_5.fillna(0); c['m9'] = c.QT_MAT_FUND_AF_9.fillna(0); c['mEMc'] = c[MAT34].fillna(0).sum(axis=1)
else:
    print('   Censo sem matrícula por série: desempate por aproximação (AI/5, AF/4, EM/3)')
    c['m5'] = c.QT_MAT_FUND_AI.fillna(0) / 5; c['m9'] = c.QT_MAT_FUND_AF.fillna(0) / 4; c['mEMc'] = c.QT_MAT_MED.fillna(0) / 3

print(f'lendo AFD {ANO} (xlsx grande, pode demorar)...')
fafd = [f for f in achar(f'AFD_ESCOLAS_{ANO}*.xlsx') if not os.path.basename(f).startswith('~$')][0]
raw = pd.read_excel(fafd, header=None, nrows=20)
hr = raw.index[raw.apply(lambda r: r.astype(str).eq('CO_ENTIDADE').any(), axis=1)][0]
a = pd.read_excel(fafd, header=hr)
a = a[num(a.CO_ENTIDADE).notna()].copy(); a['CO_ENTIDADE'] = a.CO_ENTIDADE.astype(int)
for k in ['FUN_AI_CAT_1','FUN_AF_CAT_1','MED_CAT_1']: a[k] = num(a[k])
a = a[['CO_ENTIDADE','FUN_AI_CAT_1','FUN_AF_CAT_1','MED_CAT_1']]

print(f'lendo Inse {ANO}...')
ins = pd.read_excel(achar(f'INSE_{ANO}_escolas.xlsx')[0], sheet_name=0)
PC = [f'PC_NIVEL_{k}' for k in range(1, 9)]
fp_ins = ins.set_index('ID_ESCOLA')[PC].astype(float).fillna(0)

print('lendo alunos (5EF, 9EF, EM) para a impressão digital do INSE...')
L = []
for f in ['TS_ALUNO_5EF.csv','TS_ALUNO_9EF.csv','TS_ALUNO_34EM.csv']:
    for ch in pd.read_csv(os.path.join(SAEB, f), sep=';', usecols=['ID_ESCOLA','IN_INSE','NU_TIPO_NIVEL_INSE','PESO_ALUNO_INSE'],
                          chunksize=1_000_000, low_memory=False):
        ch = ch[ch.IN_INSE == 1]; ch['PESO_ALUNO_INSE'] = num(ch.PESO_ALUNO_INSE.astype(str).str.replace(',', '.'))
        L.append(ch.groupby(['ID_ESCOLA','NU_TIPO_NIVEL_INSE']).PESO_ALUNO_INSE.sum())
w = pd.concat(L).groupby(level=[0,1]).sum().unstack(fill_value=0).reindex(columns=range(1, 9), fill_value=0)
fp_saeb = w.div(w.sum(axis=1), axis=0) * 100

def fp_diff(ids, cos):
    ids = pd.Series(ids).reset_index(drop=True); cos = pd.Series(cos).reset_index(drop=True)
    h = ids.isin(fp_saeb.index) & cos.isin(fp_ins.index)
    out = pd.Series(np.nan, index=ids.index)
    out[h] = np.abs(fp_saeb.loc[ids[h]].values - fp_ins.loc[cos[h]].values).max(axis=1)
    return out.values

# ---------------- camada A ----------------
partes = []
for et, nome in ETAPAS.items():
    d = ler_divulgacao(nome)
    t = ts[['ID_ESCOLA','ID_UF',f'MEDIA_{et}_MT',f'MEDIA_{et}_LP']].dropna().copy()
    t['mt'] = t[f'MEDIA_{et}_MT'].round(2); t['lp'] = t[f'MEDIA_{et}_LP'].round(2)
    m = t.merge(d, left_on=['ID_UF','mt','lp'], right_on=['CO_UF','mt','lp'])
    m = m[~m.ID_ESCOLA.duplicated(keep=False) & ~m.CO_ENTIDADE.duplicated(keep=False)]
    print(f'Camada A {et}: {len(m)} de {len(t)} escolas com média')
    partes.append(m[['ID_ESCOLA','CO_ENTIDADE']].assign(etapa=et))
Aall = pd.concat(partes)
g = Aall.groupby('ID_ESCOLA').agg(CO_ENTIDADE=('CO_ENTIDADE','first'), nco=('CO_ENTIDADE','nunique'),
                                   etapas_A=('etapa', lambda s: '+'.join(sorted(s))))
gc = Aall.groupby('CO_ENTIDADE').ID_ESCOLA.nunique()
print('conflitos entre etapas (mesma escola Saeb, códigos diferentes):', (g.nco > 1).sum(),
      '| mesmo código, escolas Saeb diferentes:', (gc > 1).sum())
A = g[g.nco == 1].reset_index()
A = A[~A.CO_ENTIDADE.isin(gc[gc > 1].index)][['ID_ESCOLA','CO_ENTIDADE','etapas_A']]
print('Camada A (escolas únicas):', len(A))

# ---------------- camada B ----------------
R = ts[~ts.ID_ESCOLA.isin(A.ID_ESCOLA)].copy()
pool = (c[c.TP_DEPENDENCIA.isin([1,2,3]) & (c.TP_SITUACAO_FUNCIONAMENTO == 1)]
        .merge(a, on='CO_ENTIDADE', how='left')
        .merge(ins[['ID_ESCOLA','INSE_CLASSIFICACAO','TP_CAPITAL']].rename(columns={'ID_ESCOLA':'CO_ENTIDADE'}), on='CO_ENTIDADE', how='left'))
pool = pool[~pool.CO_ENTIDADE.isin(A.CO_ENTIDADE)].copy()
R['k_ai'] = r1(R.PC_FORMACAO_DOCENTE_INICIAL); R['k_af'] = r1(R.PC_FORMACAO_DOCENTE_FINAL); R['k_med'] = r1(R.PC_FORMACAO_DOCENTE_MEDIO)
pool['k_ai'] = r1(pool.FUN_AI_CAT_1); pool['k_af'] = r1(pool.FUN_AF_CAT_1); pool['k_med'] = r1(pool.MED_CAT_1)
R['CO_UF'] = R.ID_UF; R['loc'] = R.ID_LOCALIZACAO; pool['loc'] = pool.TP_LOCALIZACAO
R['cap'] = R.ID_AREA; pool['cap'] = pool.TP_CAPITAL
R['inse'] = R.NIVEL_SOCIO_ECONOMICO.fillna('NA').str.strip(); pool['inse'] = pool.INSE_CLASSIFICACAO.fillna('NA').str.strip()
for et, col in [('5EF','m5'), ('9EF','m9'), ('EM','mEMc')]:
    R['m'+et] = R['NU_MATRICULADOS_CENSO_'+et].fillna(0); pool['m'+et] = pool[col].fillna(0)
HARD = ['CO_UF','loc','k_ai','k_af','k_med']; SOFT = ['cap','inse','m5EF','m9EF','mEM']
Pp = R[['ID_ESCOLA','ID_MUNICIPIO'] + HARD + SOFT].merge(pool[['CO_ENTIDADE','CO_MUNICIPIO'] + HARD + SOFT], on=HARD, suffixes=('','_c'))
Pp['score'] = (1*(Pp.cap == Pp.cap_c) + 2*(Pp.inse == Pp.inse_c)
               + sum((2*(Pp[m] == Pp[m+'_c']) if POR_SERIE else 0) - np.minimum((Pp[m] - Pp[m+'_c']).abs(), 50)/50 for m in ['m5EF','m9EF','mEM']))

def pick(Q, min_gap):
    Q = Q.sort_values('score', ascending=False)
    g = Q.groupby('ID_ESCOLA'); top = g.head(1).set_index('ID_ESCOLA'); sec = g.nth(1).set_index('ID_ESCOLA').score
    top['gap'] = top.score - sec.reindex(top.index).fillna(-99); top = top[top.gap >= min_gap].reset_index()
    gc = Q.groupby('CO_ENTIDADE'); ct = gc.head(1).set_index('CO_ENTIDADE'); cs = gc.nth(1).set_index('CO_ENTIDADE').score
    ct['cgap'] = ct.score - cs.reindex(ct.index).fillna(-99)
    top = top.merge(ct[['ID_ESCOLA','cgap']].reset_index(), on=['CO_ENTIDADE','ID_ESCOLA'])
    return top[(top.cgap >= min_gap) & ~top.CO_ENTIDADE.duplicated(keep=False)]

def mapa_municipios(pares):
    lk = (pares[['ID_ESCOLA','CO_ENTIDADE']].merge(ts[['ID_ESCOLA','ID_MUNICIPIO']], on='ID_ESCOLA')
          .merge(c[['CO_ENTIDADE','CO_MUNICIPIO']], on='CO_ENTIDADE'))
    return lk.groupby('ID_MUNICIPIO').CO_MUNICIPIO.apply(set), set(lk.CO_MUNICIPIO)

Bs = []
while True:
    feitos = pd.concat([A[['ID_ESCOLA','CO_ENTIDADE']]] + [b[['ID_ESCOLA','CO_ENTIDADE']] for b in Bs])
    m2r, vistos = mapa_municipios(feitos)
    Q = Pp[~Pp.ID_ESCOLA.isin(feitos.ID_ESCOLA) & ~Pp.CO_ENTIDADE.isin(feitos.CO_ENTIDADE)]
    ok = [(cm in m2r[im]) if im in m2r.index else (cm not in vistos) for im, cm in zip(Q.ID_MUNICIPIO, Q.CO_MUNICIPIO)]
    new = pick(Q[ok], 0.5)
    if len(new) == 0: break
    Bs.append(new)
B = pd.concat(Bs)[['ID_ESCOLA','CO_ENTIDADE','score','gap']]
print('Camada B:', len(B))

# ---------------- camada C ----------------
feitos = pd.concat([A[['ID_ESCOLA','CO_ENTIDADE']], B[['ID_ESCOLA','CO_ENTIDADE']]])
m2r, vistos = mapa_municipios(feitos)
resto = R[~R.ID_ESCOLA.isin(B.ID_ESCOLA)]
livre = pool[~pool.CO_ENTIDADE.isin(feitos.CO_ENTIDADE)]
ins_livre = ins[~ins.ID_ESCOLA.isin(feitos.CO_ENTIDADE)]
Crows, cand_rows = [], []
for _, r in resto.iterrows():
    p = livre[(livre.CO_UF == r.ID_UF) & (livre['loc'] == r.ID_LOCALIZACAO)]
    p = p[p.CO_MUNICIPIO.isin(m2r[r.ID_MUNICIPIO])] if r.ID_MUNICIPIO in m2r.index else p[~p.CO_MUNICIPIO.isin(vistos)]
    p = p[(p.k_ai == r.k_ai) & (p.k_af == r.k_af) & (p.k_med == r.k_med)]
    for _, q in p.iterrows():
        cand_rows.append((r.ID_ESCOLA, q.CO_ENTIDADE, q.NO_ENTIDADE, q.CO_MUNICIPIO,
                          r.m5EF, q.m5EF, r.m9EF, q.m9EF, r.mEM, q.mEM))
    if r.ID_ESCOLA in fp_saeb.index:
        sub = ins_livre[ins_livre.CO_UF == r.ID_UF]
        if len(sub):
            dd = np.abs(sub[PC].astype(float).fillna(0).values - fp_saeb.loc[r.ID_ESCOLA].values).max(axis=1)
            o = np.argsort(dd)
            if dd[o[0]] <= 0.011 and (len(o) == 1 or dd[o[1]] > 0.011) and sub.ID_ESCOLA.values[o[0]] in set(p.CO_ENTIDADE):
                Crows.append((r.ID_ESCOLA, sub.ID_ESCOLA.values[o[0]]))
C = pd.DataFrame(Crows, columns=['ID_ESCOLA','CO_ENTIDADE'])
C = C[~C.CO_ENTIDADE.duplicated(keep=False)]
print('Camada C:', len(C))

# ---------------- montagem e validação ----------------
X = pd.concat([A.assign(camada='A', metodo='proficiencia x IDEB (' + A.etapas_A + ')'),
               B.assign(camada='B', metodo='AFD+municipio+INSE+matriculas'),
               C.assign(camada='C', metodo='impressao digital INSE + AFD+municipio')], ignore_index=True)
X['valid_inse_maxdif_pp'] = np.round(fp_diff(X.ID_ESCOLA, X.CO_ENTIDADE), 4)
X['valid_inse'] = np.where(X.valid_inse_maxdif_pp.isna(), 'sem impressao digital',
                           np.where(X.valid_inse_maxdif_pp <= 0.011, 'confirma', 'diverge'))
X['confianca'] = np.select([X.camada.eq('A'), X.valid_inse.eq('diverge'), X.valid_inse.eq('confirma')],
                           ['muito alta', 'revisar', 'alta'], 'media')
print(pd.crosstab(X.camada, X.valid_inse))
cols_ts = ['ID_ESCOLA','ID_UF','ID_MUNICIPIO','ID_AREA','ID_LOCALIZACAO']
for et in ['5EF','9EF','EM']:
    cols_ts += [f'NU_MATRICULADOS_CENSO_{et}', f'NU_PRESENTES_{et}', f'MEDIA_{et}_LP', f'MEDIA_{et}_MT']
X = (X.merge(ts[cols_ts], on='ID_ESCOLA', how='left')
      .merge(c[['CO_ENTIDADE','NO_ENTIDADE','CO_MUNICIPIO','TP_DEPENDENCIA','TP_LOCALIZACAO']], on='CO_ENTIDADE', how='left'))
for et in ['5EF','9EF','EM']:
    X[f'IN_{et}'] = (X[f'NU_MATRICULADOS_CENSO_{et}'].fillna(0).gt(0) | X[f'NU_PRESENTES_{et}'].notna()).astype(int)
X = X.drop(columns=['etapas_A','TP_LOCALIZACAO']).rename(columns={
    'ID_ESCOLA':'ID_ESCOLA_SAEB_MASCARA','CO_ENTIDADE':'CO_ENTIDADE_INEP','ID_MUNICIPIO':'ID_MUNICIPIO_SAEB_MASCARA',
    'CO_MUNICIPIO':'CO_MUNICIPIO_IBGE_CENSO','score':'score_B','gap':'folga_B'})
os.makedirs(OUT, exist_ok=True)
X.to_csv(os.path.join(OUT, f'crosswalk_saeb{ANO}_escolas.csv'), sep=';', index=False, encoding='utf-8-sig', decimal=',')

nm = ts[~ts.ID_ESCOLA.isin(X.ID_ESCOLA_SAEB_MASCARA)]
cand = pd.DataFrame(cand_rows, columns=['ID_ESCOLA_SAEB_MASCARA','CO_ENTIDADE_candidata','NO_ENTIDADE','CO_MUNICIPIO_IBGE',
                                        'mat5_saeb','mat5_censo','mat9_saeb','mat9_censo','matEM_saeb','matEM_censo'])
cand = cand[cand.ID_ESCOLA_SAEB_MASCARA.isin(nm.ID_ESCOLA)]
(nm[['ID_ESCOLA','ID_UF','ID_MUNICIPIO','ID_LOCALIZACAO','NIVEL_SOCIO_ECONOMICO','PC_FORMACAO_DOCENTE_INICIAL',
     'PC_FORMACAO_DOCENTE_FINAL','PC_FORMACAO_DOCENTE_MEDIO']].rename(columns={'ID_ESCOLA':'ID_ESCOLA_SAEB_MASCARA'})
   .merge(cand, on='ID_ESCOLA_SAEB_MASCARA', how='left')
   .to_csv(os.path.join(OUT, f'saeb{ANO}_nao_pareadas_candidatas.csv'), sep=';', index=False, encoding='utf-8-sig', decimal=','))

print('\nResumo por etapa (escolas do TS_ESCOLA com matrícula ou presença na etapa):')
for et in ['5EF','9EF','EM']:
    u = ts[ts[f'NU_MATRICULADOS_CENSO_{et}'].fillna(0).gt(0) | ts[f'NU_PRESENTES_{et}'].notna()]
    print(f'  {et}: universo {len(u)} | recuperadas {u.ID_ESCOLA.isin(X.ID_ESCOLA_SAEB_MASCARA).sum()}')
print('TOTAL TS_ESCOLA:', len(ts), '| recuperadas:', len(X), '| não pareadas:', len(nm))
