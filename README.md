# As máscaras estão caindo

**Como recuperar o código INEP das escolas do Saeb 2023 usando apenas dados públicos do próprio Inep.**

Desde o Saeb 2021, o Inep publica os microdados do Saeb com códigos fictícios ("máscaras") de escola e de município, em nome da LGPD. Este repositório mostra que os outros arquivos públicos do Inep desfazem essa máscara: recuperamos o código verdadeiro de **70.112 das 70.151 escolas** dos microdados do Saeb 2023 (**99,94%**). Nenhum dos testes de validade apontou um par errado.

| Série avaliada | Escolas no Saeb | Escolas recuperadas |
| --- | ---: | ---: |
| 5º ano do EF | 44.248 | 44.222 (99,94%) |
| 9º ano do EF | 36.355 | 36.347 (99,98%) |
| Ensino médio | 19.092 | 19.085 (99,96%) |
| **Todas (sem repetir escolas)** | **70.151** | **70.112 (99,94%)** |

Uma escola entra numa linha quando tem matrícula ou alunos presentes naquela série. A linha "Todas" conta cada escola uma vez.

- Texto para o público geral: [`docs/as_mascaras_estao_caindo.pdf`](docs/as_mascaras_estao_caindo.pdf)
- Tabela de correspondência: [`dados/crosswalk_saeb2023_escolas.csv`](dados/crosswalk_saeb2023_escolas.csv)

---

## Por que isso importa

O código da escola é o que liga o Saeb a qualquer outra base. Sem ele, os questionários de alunos, professores e diretores não se cruzam com o Censo Escolar, com a lista de escolas atendidas por um programa ou com os dados de uma avaliação de impacto. As notas por escola, por outro lado, continuam publicadas com o código verdadeiro nas planilhas do Ideb. A máscara tira o acesso de quem faz pesquisa e não impede a reidentificação das escolas.

## Como funciona

O princípio é simples: se uma estatística da escola aparece nos microdados mascarados e também num arquivo com o código verdadeiro, ela serve de ponte entre os dois. O método tem três camadas, da mais segura para a menos segura. Cada camada trabalha só com o que sobrou da anterior e só aceita pares 1 para 1.

| Camada | Chave | Escolas |
| --- | --- | ---: |
| **A. Proficiência** | UF + média de Matemática + média de Língua Portuguesa da escola (`TS_ESCOLA`) × notas Saeb 2023 das planilhas do Ideb por escola, separadamente para 5º ano, 9º ano e EM | 64.448 |
| **B. Chaves administrativas** | UF + localização + % de adequação da formação docente (AFD) em anos iniciais, anos finais e EM, todos obrigatórios; município coerente com o mapa de máscaras; desempate por capital/interior, classificação do Inse e matrículas do Censo | 5.660 |
| **C. Impressão digital do Inse** | Distribuição dos alunos pelos 8 níveis do Inse, recalculada dos microdados, × arquivo do Inse por escola, só quando aponta uma única escola que também passa nas chaves da camada B | 4 |
| Não pareadas | Escolas com "gêmeas" idênticas nos dados públicos | 39 |

**Mapa de municípios.** O Inep usa sempre a mesma máscara para cada município, em todas as bases. Cada escola pareada na camada A revela qual município real está por trás de uma máscara; com isso, 5.555 das 5.569 máscaras ficam conhecidas. Na camada B, a escola candidata precisa estar no município correspondente à máscara.

### Critérios de comparação

| Chave | Precisão publicada | Regra | Papel |
| --- | --- | --- | --- |
| UF | código IBGE (real no Saeb) | igualdade exata | obrigatória em A, B, C |
| Médias de MT e LP | até 2 casas nos dois arquivos | **igualdade exata, sem tolerância** | chave da camada A |
| Localização | urbana/rural | igualdade exata | obrigatória em B, C |
| % adequação docente (AI, AF, EM) | 1 casa nos dois arquivos | igualdade exata; vazio só casa com vazio | obrigatória em B, C |
| Município | máscara × IBGE | máscara já revelada: o mesmo município; máscara ainda não revelada: município ainda não usado | obrigatória em B, C |
| Capital/interior | código | igualdade: +1 ponto | desempate em B |
| Classificação do Inse | Nível I a VIII | igualdade: +2 pontos | desempate em B |
| Matrículas (5º ano, 9º ano, 3ª+4ª série EM) | inteiro | igualdade: +2; diferença: −dif/50, no máximo −1 | desempate em B |
| Aceitação em B | — | vencedora com folga ≥ 0,5 ponto sobre a segunda, nos dois sentidos | regra de decisão |
| Distribuição do Inse (8 níveis) | 2 casas no arquivo do Inse | diferença máxima ≤ 0,011 p.p. | chave em C e teste das demais |

A única tolerância do método está na comparação do Inse. Ela compara uma distribuição recalculada, sem arredondamento, com a distribuição publicada, arredondada a duas casas. O erro esperado é de no máximo 0,005 p.p., e a folga até 0,011 cobre imprecisão de ponto flutuante.

## Como sabemos que está certo

`validar_crosswalk.py` reproduz todos os números abaixo.

**1. Unicidade da chave da camada A.** Dentro da UF, quase nenhuma combinação de médias de MT e LP se repete.

| Etapa | Escolas com média | Combinações UF+MT+LP distintas | Escolas em combinação repetida | Sem UF (só MT+LP) | Únicas usando só UF+MT |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5º ano | 41.281 | 41.278 | 6 | 60 | 29.974 (72,6%) |
| 9º ano | 31.080 | 31.079 | 2 | 56 | 23.142 (74,5%) |
| EM | 14.431 | 14.431 | 0 | 4 | 11.678 (80,9%) |

As 8 escolas empatadas ficaram fora da camada A e foram resolvidas na camada B.

**2. Placebo com outras edições.** Repetimos a camada A trocando as notas de 2023 pelas de outras edições, publicadas nas mesmas planilhas. Se as coincidências fossem acaso, outras edições também gerariam pares.

| Notas usadas | 2017 | 2019 | 2021 | **2023** | 2025 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Escolas pareadas (5º + 9º + EM) | 13 | 16 | 9 | **86.792** | 9 |

**3. Variáveis não usadas na camada A.** Nos 64.448 pares da camada A, comparamos o que o Saeb diz da escola com o que o arquivo de código real diz da escola pareada.

| Variável | Concordância |
| --- | ---: |
| Localização (Censo) | 100,00% |
| % adequação docente: anos iniciais, anos finais, EM (AFD) | 100,00% |
| Capital/interior (Inse) | 99,96% |
| Classificação do Inse | 99,89% |
| Matrículas do 9º ano (Censo) | 98,19% |
| Matrículas da 3ª+4ª série do EM (Censo) | 97,71% |
| Matrículas do 5º ano (Censo) | 97,20% |

**4. Consistência entre etapas.** Pareamos 21.170 escolas de forma independente em duas ou três etapas, cada uma com sua própria planilha de notas. Todas receberam o mesmo código em todas as etapas, sem nenhum conflito.

**5. Impressão digital do Inse.** Em todos os 64.423 pares da camada A em que o teste é possível, a maior diferença entre os 8 níveis é ≤ 0,005 p.p., ou seja, só arredondamento. A escola mais parecida que não é o par fica, na mediana, a 2,25 p.p. A camada B não usa o Inse e, mesmo assim, ele confirma todos os 5.327 pares da camada B que têm esse dado. Somando as camadas, são 69.754 pares conferidos e nenhum divergente. Pela regra do três, a taxa de erro é de no máximo 0,004% (IC 95%).

## Saeb 2021

O mesmo método, aplicado ao Saeb 2021, recupera **70.784 das 70.897 escolas (99,84%)**: 49.202 pela proficiência (camada A), 21.027 pela camada B e 555 pela impressão digital do Inse (camada C). O Censo Escolar 2021 não traz matrículas por série, então o desempate da camada B usa uma aproximação pela matrícula da etapa. No placebo, as notas de outros anos pareiam no máximo 6 escolas por etapa.

A impressão digital do Inse confirma 69.816 pares e aponta **1 divergência**, na camada B (escola `61354139`). Essa linha está marcada com `confianca = revisar`. Outros 967 pares não têm Inse para conferir (949 da camada B e 18 da camada A).

As máscaras de escola e de município mudam de uma edição para outra: nenhum código fictício se repete entre 2021 e 2023. Com os dois crosswalks, 66.606 escolas podem ser seguidas de uma edição à outra pelo código INEP.

## Estrutura do repositório

```
recuperar_id_saeb.py         # gera o crosswalk de um ano a partir dos arquivos do Inep (alguns minutos)
validar_crosswalk.py         # reproduz os testes de validade de um ano (alguns minutos)
dados/
  crosswalk_saeb2023_escolas.csv          # 70.112 pares (separador ;, decimal ,, UTF-8)
  saeb2023_nao_pareadas_candidatas.csv    # 39 escolas não pareadas e suas candidatas
  crosswalk_saeb2021_escolas.csv          # 70.784 pares
  saeb2021_nao_pareadas_candidatas.csv    # 113 escolas não pareadas e suas candidatas
docs/
  as_mascaras_estao_caindo.pdf            # texto para o público geral
```

### Colunas principais do crosswalk

| Coluna | Descrição |
| --- | --- |
| `ID_ESCOLA_SAEB_MASCARA` | código fictício da escola nos microdados do Saeb 2023 (junta com `TS_ESCOLA`, `TS_ALUNO_*`, `TS_DIRETOR`, `TS_PROFESSOR`) |
| `CO_ENTIDADE_INEP` | código INEP verdadeiro da escola (junta com o Censo Escolar, as planilhas do Ideb, a AFD e o Inse) |
| `camada`, `metodo` | camada em que o par foi formado e, na camada A, as etapas usadas |
| `score_B`, `folga_B` | pontuação e folga do par na camada B |
| `valid_inse`, `valid_inse_maxdif_pp` | resultado do teste da impressão digital do Inse (`confirma` / `sem impressao digital`) |
| `confianca` | `muito alta` (A), `alta` (B ou C confirmados pelo Inse), `media` (B sem Inse para checar, 333 escolas) |
| `IN_5EF`, `IN_9EF`, `IN_EM` | 1 se a escola tem matrícula ou presença na etapa |
| `ID_MUNICIPIO_SAEB_MASCARA`, `CO_MUNICIPIO_IBGE_CENSO` | município mascarado e município real |

## Como reproduzir

1. Instale as dependências: `pip install -r requirements.txt` (Python 3.10+).
2. Baixe os arquivos do Inep, todos públicos, para uma pasta. O script procura os arquivos pelo nome em todas as subpastas, então a organização é livre; o caminho dos microdados do Saeb só precisa conter "saeb" e o ano. Um exemplo:

```
<pasta_dados>/
  microdados_saeb_2023/MICRODADOS_SAEB_2023/DADOS/          TS_ESCOLA.csv, TS_ALUNO_5EF.csv, TS_ALUNO_9EF.csv, TS_ALUNO_34EM.csv
  divulgacao_anos_iniciais_escolas_2025/divulgacao_anos_iniciais_escolas_2025/divulgacao_anos_iniciais_escolas_2025.xlsx
  divulgacao_anos_finais_escolas_2025/divulgacao_anos_finais_escolas_2025/divulgacao_anos_finais_escolas_2025.xlsx
  divulgacao_ensino_medio_escolas_2025/divulgacao_ensino_medio_escolas_2025/divulgacao_ensino_medio_escolas_2025.xlsx
  microdados_censo_escolar_2023/microdados_censo_escolar_2023/dados/microdados_ed_basica_2023.csv
  AFD_2023_ESCOLAS/AFD_2023_ESCOLAS/AFD_ESCOLAS_2023_v1.1.xlsx
  INSE_2023_escolas.xlsx
```

   - [Microdados do Saeb e do Censo Escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados)
   - [Resultados do Ideb por escola](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados)
   - [Indicadores educacionais (AFD e Inse)](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais)

3. Rode:

```bash
python3 recuperar_id_saeb.py <pasta_dados> 2023 saida/
python3 validar_crosswalk.py <pasta_dados> 2023 saida/crosswalk_saeb2023_escolas.csv
```

   Para outro ano (testado em 2021), troque o ano e tenha na pasta o Saeb, o Censo Escolar, a AFD e o Inse daquele ano. As planilhas do Ideb da edição 2025 já trazem as notas de 2017 a 2025.

Os arquivos de alunos (cerca de 3 GB) são lidos em blocos; um computador comum com 4 GB de RAM dá conta.

## Limitações

- **39 escolas não pareadas.** São quase todas rurais e pequenas, sem alunos com Inse, e têm de 2 a 68 "gêmeas" idênticas no mesmo município.
- **333 pares de confiança média.** Vêm da camada B, em escolas sem Inse, e não têm teste independente. Para análises sensíveis, rode com e sem eles.
- **Dependência da divulgação.** A camada A depende de as planilhas do Ideb trazerem as notas com duas casas decimais. Se isso mudar, o método passa a depender das camadas B e C.
- **Escopo testado.** Testamos só o Saeb 2023, o 5º e o 9º ano e o EM, e só escolas públicas.

## Uso responsável

O que se recupera é o **código da escola**. Os microdados do Saeb não têm nome, CPF, endereço ou data de nascimento de ninguém, e isso não muda. As escolas já têm seus resultados divulgados nominalmente pelo Inep. Use esta base para análises sobre escolas e redes, não para expor turmas ou professores, e observe os termos de uso dos microdados do Inep.

## Contexto

- Inep, *Leia-me dos Microdados do Saeb 2023*, seção "Proteção dos dados pessoais".
- [Correio Braziliense (22/02/2022): Inep remove microdados do Censo Escolar e do Enem e oculta informações](https://www.correiobraziliense.com.br/euestudante/enem/2022/02/4987511-inep-remove-microdados-do-censo-escolar-e-do-enem-e-oculta-informacoes.html)
- [ANPEd (2023): moção pela revisão da aplicação da LGPD pelo Inep](https://legado.anped.org.br/sites/default/files/images/mocao_08_oficio_anped_082-2023_mocao_pela_revisao_da_atual_interpretacao_e_aplicacao_da_lei_geral_de_protecao_de_dados_pessoais_lgpd_pelo_inep.pdf)
- [Open Knowledge Brasil e Fundação Lemann (2025): microdados educacionais, da transparência à opacidade](https://ok.org.br/noticia/relatorio-okbr-lemann-microdados-educacionais/)

## Licença e citação

- Código: MIT (ver `LICENSE`).
- Tabelas em `dados/` e textos em `docs/`: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt-br).

> Camelo, Rafael. *As máscaras estão caindo: recuperação do código INEP das escolas do Saeb 2021 e 2023 com dados públicos.* 2026. Disponível em: https://github.com/rafaelcamelo/saeb-mascara
