# -*- coding: utf-8 -*-
"""
Testes de validade do crosswalk do Saeb (2021 em diante) (escola mascarada -> código INEP).

Uso:  python3 validar_crosswalk.py <pasta_dados> <ano> <crosswalk_saeb<ano>_escolas.csv>

Reproduz os números do README:
  1. Unicidade da chave UF + MT + LP (camada A)
  2. Placebo: pareamento com notas de outras edições (2017, 2019, 2021, 2025)
  3. Concordância de variáveis não usadas na camada A (localização, AFD, Inse, matrículas)
  4. Consistência entre etapas (mesma escola pareada por 5EF, 9EF e EM)
  5. Impressão digital do Inse: distância do par verdadeiro x escola mais parecida
"""
import sys, os, glob, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

BASE = sys.argv[1] if len(sys.argv) > 1 else '.'
ANO = str(sys.argv[2]) if len(sys.argv) > 2 else '2023'
XW = sys.argv[3] if len(sys.argv) > 3 else os.path.join('dados', f'crosswalk_saeb{ANO}_escolas.csv')
num = lambda s: pd.to_numeric(s, errors='coerce')
UF = {'RO':11,'AC':12,'AM':13,'RR':14,'PA':15,'AP':16,'TO':17,'MA':21,'PI':22,'CE':23,'RN':24,'PB':25,'PE':26,
      'AL':27,'SE':28,'BA':29,'MG':31,'ES':32,'RJ':33,'SP':35,'PR':41,'SC':42,'RS':43,'MS':50,'MT':51,'GO':52,'DF':53}
ETAPAS = {'5EF': 'divulgacao_anos_iniciais_escolas_', '9EF': 'divulgacao_anos_finais_escolas_',
          'EM': 'divulgacao_ensino_medio_escolas_'}
MAT34 = ['QT_MAT_MED_PROP_3','QT_MAT_MED_PROP_4','QT_MAT_MED_CT_3','QT_MAT_MED_CT_4','QT_MAT_MED_NM_3','QT_MAT_MED_NM_4']
pct = lambda x: f'{100 * x:.2f}%'
achar = lambda padrao: sorted(glob.glob(os.path.join(BASE, '**', padrao), recursive=True))
SAEB = os.path.dirname([f for f in achar('TS_ESCOLA.csv') if 'saeb' in f.lower() and ANO in f][0])
ANOS_PLACEBO = ['2017', '2019', '2021', '2023', '2025']

ts = pd.read_csv(os.path.join(SAEB, 'TS_ESCOLA.csv'), sep=';', encoding='latin1', low_memory=False)
X = pd.read_csv(XW, sep=';', decimal=',')
A = X[X.camada == 'A']

def ler_divulgacao(prefixo):
    for f in sorted(achar(prefixo + '*.xlsx'), reverse=True):
        raw = pd.read_excel(f, header=None, nrows=15)
        hr = raw.index[raw.apply(lambda r: r.astype(str).eq('ID_ESCOLA').any(), axis=1)][0]
        d = pd.read_excel(f, header=hr, dtype=str)
        if f'VL_NOTA_MATEMATICA_{ANO}' not in d.columns: continue
        d = d[d.ID_ESCOLA.str.match(r'^\d+$', na=False)].copy()
        d['uf'] = d.SG_UF.map(UF)
        return d
    sys.exit(f'nenhuma divulgação {prefixo}*.xlsx traz as notas de {ANO}')

print('\n=== 1-2. Unicidade da chave e placebo com outras edições ===')
for et, nome in ETAPAS.items():
    d = ler_divulgacao(nome)
    t = ts[['ID_ESCOLA','ID_UF',f'MEDIA_{et}_MT',f'MEDIA_{et}_LP']].dropna().copy()
    t['mt'] = t[f'MEDIA_{et}_MT'].round(2); t['lp'] = t[f'MEDIA_{et}_LP'].round(2)
    k = t.groupby(['ID_UF','mt','lp']).size(); k2 = t.groupby(['mt','lp']).size(); k1 = t.groupby(['ID_UF','mt']).size()
    print(f'{et}: {len(t)} escolas com média | combinações UF+MT+LP: {len(k)} | escolas em combinação repetida: '
          f'{int(k[k > 1].sum())} | sem UF: {int(k2[k2 > 1].sum())} | únicas só com UF+MT: {int(k1[k1 == 1].sum())}')
    linha = []
    for ano in [x for x in ANOS_PLACEBO if f'VL_NOTA_MATEMATICA_{x}' in d.columns]:
        dd = d.assign(mt=num(d[f'VL_NOTA_MATEMATICA_{ano}']), lp=num(d[f'VL_NOTA_PORTUGUES_{ano}'])).dropna(subset=['mt','lp'])
        m = t.merge(dd[['uf','mt','lp']], left_on=['ID_UF','mt','lp'], right_on=['uf','mt','lp'])
        linha.append(f'{ano}: {m.ID_ESCOLA.nunique()}')
    print('   placebo (escolas pareadas com as notas de cada edição) ->', ' | '.join(linha))

print('\n=== 3. Concordância de variáveis não usadas na camada A ===')
fcenso = achar(f'microdados_ed_basica_{ANO}.csv')[0]
cab = pd.read_csv(fcenso, sep=';', encoding='latin1', nrows=0).columns
POR_SERIE = 'QT_MAT_FUND_AI_5' in cab
extra = (['QT_MAT_FUND_AI_5','QT_MAT_FUND_AF_9'] + MAT34) if POR_SERIE else []
c = pd.read_csv(fcenso, sep=';', encoding='latin1', low_memory=False, usecols=['CO_ENTIDADE','TP_LOCALIZACAO'] + extra)
if POR_SERIE: c['s34'] = c[MAT34].fillna(0).sum(axis=1)
fafd = [f for f in achar(f'AFD_ESCOLAS_{ANO}*.xlsx') if not os.path.basename(f).startswith('~$')][0]
raw = pd.read_excel(fafd, header=None, nrows=20)
a = pd.read_excel(fafd, header=raw.index[raw.apply(lambda r: r.astype(str).eq('CO_ENTIDADE').any(), axis=1)][0])
a = a[num(a.CO_ENTIDADE).notna()].copy(); a['CO_ENTIDADE'] = a.CO_ENTIDADE.astype(int)
for col in ['FUN_AI_CAT_1','FUN_AF_CAT_1','MED_CAT_1']: a[col] = num(a[col])
ins = pd.read_excel(achar(f'INSE_{ANO}_escolas.xlsx')[0], sheet_name=0)
V = (A[['ID_ESCOLA_SAEB_MASCARA','CO_ENTIDADE_INEP']]
     .merge(ts, left_on='ID_ESCOLA_SAEB_MASCARA', right_on='ID_ESCOLA')
     .merge(c, left_on='CO_ENTIDADE_INEP', right_on='CO_ENTIDADE', how='left')
     .merge(a, on='CO_ENTIDADE', how='left')
     .merge(ins[['ID_ESCOLA','INSE_CLASSIFICACAO','TP_CAPITAL']].rename(columns={'ID_ESCOLA':'CO_ENTIDADE'}), on='CO_ENTIDADE', how='left'))
r1 = lambda s: s.round(1).fillna(-1)
testes = [('Localização', V.ID_LOCALIZACAO == V.TP_LOCALIZACAO),
          ('AFD anos iniciais', r1(V.PC_FORMACAO_DOCENTE_INICIAL) == r1(V.FUN_AI_CAT_1)),
          ('AFD anos finais', r1(V.PC_FORMACAO_DOCENTE_FINAL) == r1(V.FUN_AF_CAT_1)),
          ('AFD ensino médio', r1(V.PC_FORMACAO_DOCENTE_MEDIO) == r1(V.MED_CAT_1)),
          ('Capital/interior', V.ID_AREA == V.TP_CAPITAL),
          ('Classificação Inse', V.NIVEL_SOCIO_ECONOMICO.str.strip() == V.INSE_CLASSIFICACAO.str.strip())]
for et, col in ([('5EF','QT_MAT_FUND_AI_5'), ('9EF','QT_MAT_FUND_AF_9'), ('EM','s34')] if POR_SERIE else []):
    h = V[V[f'NU_MATRICULADOS_CENSO_{et}'].notna()]
    testes.append((f'Matrículas {et}', (h[f'NU_MATRICULADOS_CENSO_{et}'] == h[col].fillna(0))))
for nome, s in testes:
    print(f'{nome:<22} {pct(s.mean())}  (n={len(s)})')

print('\n=== 4. Consistência entre etapas ===')
print(A.metodo.value_counts().to_string())
print('(O script de pareamento descarta qualquer escola com códigos diferentes entre etapas; o log dele informa 0 conflitos.)')

print('\n=== 5. Impressão digital do Inse ===')
L = []
for f in ['TS_ALUNO_5EF.csv','TS_ALUNO_9EF.csv','TS_ALUNO_34EM.csv']:
    for ch in pd.read_csv(os.path.join(SAEB, f), sep=';', usecols=['ID_ESCOLA','IN_INSE','NU_TIPO_NIVEL_INSE','PESO_ALUNO_INSE'],
                          chunksize=1_000_000, low_memory=False):
        ch = ch[ch.IN_INSE == 1]; ch['PESO_ALUNO_INSE'] = num(ch.PESO_ALUNO_INSE.astype(str).str.replace(',', '.'))
        L.append(ch.groupby(['ID_ESCOLA','NU_TIPO_NIVEL_INSE']).PESO_ALUNO_INSE.sum())
w = pd.concat(L).groupby(level=[0,1]).sum().unstack(fill_value=0).reindex(columns=range(1, 9), fill_value=0)
fp_s = w.div(w.sum(axis=1), axis=0) * 100
PC = [f'PC_NIVEL_{k}' for k in range(1, 9)]
Ai = A[['ID_ESCOLA_SAEB_MASCARA','CO_ENTIDADE_INEP','ID_UF']].rename(columns={'ID_ESCOLA_SAEB_MASCARA':'ID_ESCOLA'})
Ai = Ai[Ai.ID_ESCOLA.isin(fp_s.index) & Ai.CO_ENTIDADE_INEP.isin(ins.ID_ESCOLA)]
res = []
for uf, g in Ai.groupby('ID_UF'):
    ii = ins[ins.CO_UF == uf]; Y = ii[PC].astype(float).fillna(0).values; cod = ii.ID_ESCOLA.values
    for co, x in zip(g.CO_ENTIDADE_INEP.values, fp_s.loc[g.ID_ESCOLA].values):
        dd = np.abs(Y - x).max(axis=1)
        res.append((dd[cod == co][0], dd[cod != co].min()))
R = pd.DataFrame(res, columns=['par_verdadeiro', 'mais_parecida'])
print(f'pares testados: {len(R)} | par verdadeiro: máx {R.par_verdadeiro.max():.4f} p.p. | '
      f'escola mais parecida que não é o par: mediana {R.mais_parecida.median():.2f} p.p.')
print(pd.cut(R.mais_parecida, [0, 0.011, 0.5, 1, 2, 5, 10, 100], include_lowest=True).value_counts().sort_index().to_string())
print('\nResumo da validação no crosswalk:'); print(pd.crosstab(X.camada, X.valid_inse).to_string())
