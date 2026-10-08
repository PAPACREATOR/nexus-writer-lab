# Nexus Writer Lab — bancada isolada

**Sem autoridade de produção. Writer dentro de LPAC/Job ainda não tem solução demonstrada.**

Este repositório é o laboratório de diagnóstico de `book` e `convert_pdf` em
Windows. Origem imutável: `PAPACREATOR/cerebro-parvo-`, commit
`b4d50ab8469cf60dfa3228c7c34ef9a1285ac827`. O commit inicial do laboratório
`3f4e085a12b551ccf99a80f503e08aae03b1b833` acrescenta apenas a proveniência.

- [Proveniência e baseline](SOURCE_BASELINE.md)
- [Relatório](LAB_REPORT.md)
- [Matriz de experiências](RESULT_MATRIX.md)
- [Evidência de rastreio](TRACE_EVIDENCE.md)
- [Proposta mínima](MINIMAL_PATCH_PROPOSAL.md) — fica vazia enquanto não existir solução reproduzível
- [Execuções e artefactos](https://github.com/PAPACREATOR/nexus-writer-lab/actions)

Os workflows `Writer isolated sequential matrix` e `Writer isolated ETW trace`
usam o instalador oficial arquivado **26.2.6.2**, com SHA-256 fixado. O candidato
já usa UserInstallation dedicado, diretório pré-criado, ACL herdada do SID da
tarefa e `--norestore`: B–E são repetições equivalentes, identificadas como tal.
F acrescenta somente `--nolockcheck`; G acrescenta somente `--nologo` a F.
H exige uma combinação mínima justificada pelos resultados; não foi executada.
A alternativa I usa LibreOfficeKit oficial e permanece sem PASS reproduzível.

O prazo Writer permanece **45 segundos**. Host, Kernel, Store, LPAC, Job,
Human Gate, Creative/Canonical, recovery e contratos permanecem os do SHA
original. F/G alteram apenas flags do adapter numa cópia experimental descartável;
o selo dessa cópia é atualizado explicitamente e os bytes originais são restaurados
no fim. I altera somente o adapter selado numa cópia experimental; as rotas
reais falharam também numa conta normal. Nenhuma alteração experimental é
aplicada ao repositório principal. A Folha e a regressão 100+100 de uma solução
continuam pendentes do gate positivo de Writer.

A hipótese externa de Carlos De La Torre / @radelqui está referenciada no
[comentário técnico](https://github.com/PAPACREATOR/cerebro-parvo-/issues/36#issuecomment-6064316804).
Os resultados são classificados como PROVEN, LIKELY, NOT PROVEN ou REFUTED.
Um ACCESS DENIED isolado não prova a causa do timeout.

Para repetir, despachar os workflows neste repositório. Não executar instaladores
de diagnóstico no PC pessoal: os workflows preparam runners Windows descartáveis.
Para contribuir, abrir issues/PRs **aqui**, com variante, SHA, build, comandos,
evidência e resultado. Não editar ou fazer push para `PAPACREATOR/cerebro-parvo-`.

Os documentos Nexus abaixo e nas pastas existentes são contexto histórico do
candidato, não uma declaração de aprovação do laboratório.

---

# README original do candidato (preservado)

Sistema local-first de criação, conhecimento e execução governada para uma pessoa. A pessoa usa linguagem natural; o sistema compõe processos e ferramentas nos bastidores; a pessoa continua autoridade final.

## Código desta versão

O protótipo Windows está em [nexus/](nexus/README.md). Consultar o [estado testado e pendências](nexus/docs/PONTO-DE-SITUACAO.md). As pastas `implementacao/` e `historico/` conservam versões anteriores; não são necessárias para executar Nexus.

## Estado atual em uma frase

**Protótipo candidato: Folha em linguagem natural + Kernel/Host/Store Python + MCP determinístico + ferramentas externas + Creative/Human Gate/Canonical.**

A continuação está na [PR #23](https://github.com/PAPACREATOR/cerebro-parvo-/pull/23), branch `lab-open-notebook-avatar-20261004`; ainda não é a versão integrada em `main`. PASS de uma suite não significa release. O [ponto de situação](nexus/docs/PONTO-DE-SITUACAO.md) distingue a última referência verde, os testes do SHA analisado e os gates pendentes.

A arquitetura conceptual está estável. A implementação física continua sujeita a testes: nenhuma integração é declarada resolvida antes de PASS real.

## Modelo mental

Nexus é um **launcher metódico, com memória, leis e templates executáveis**, que usa as ferramentas disponíveis para atingir um fim. Não tenta reprogramar capacidades maduras.

A pessoa escreve na Folha. Kernel/Host/Store validam e executam o processo; MCP transporta chamadas às ferramentas. Os resultados são verificados e guardados em Creative. Só decisão humana permite promoção para Canonical. O percurso completo de cada capacidade exige prova própria.


## Separação de responsabilidades

As responsabilidades M1–M14 continuam aplicáveis. Os contratos, testes e a evidência datada da implementação estão em `nexus/docs/`.

### Folha Nexus
Interface inicial mínima. Texto natural, anexos, resultados e decisões humanas. YAML, JSON, Markdown, IDs e infraestrutura ficam escondidos na utilização normal.

### Kernel e MCP
O runtime candidato usa Kernel/Host/Store Python. MCP é transporte determinístico, sem IA nem autoridade de aprovação. Conductor/Spiff foram retirados do runtime ativo; as comparações e decisões anteriores permanecem como genealogia, incluindo a [PR #21](https://github.com/PAPACREATOR/cerebro-parvo-/pull/21).

### Open Notebook
**Bancada de trabalho, ponto.** Não é memória soberana, Canonical, Creative, arquivo, Wiki, autoridade nem interface principal. Recebe um pacote de trabalho limitado, permite trabalho cognitivo com tiny local e devolve resultado estruturado. Deve poder ser destruído/substituído sem perda de conhecimento Nexus.

### Nexus / Windows
É dono da memória e da continuidade: Raw/entrada, Creative, Canonical, arquivo, proveniência, eventos, regras, processos/templates, schemas e histórico. Formatos preferidos: Markdown + JSON + YAML + fontes originais/hashes; SQLite/FTS5 pode ser usado como índice/estado quando justificar, sem tornar a memória dependente de uma aplicação externa.

### Capabilities
LibreOffice, Zotero, LanguageTool, web, imagem, áudio, Whisper/TTS e outras ferramentas entram apenas quando um processo precisa delas. `LIGAR > CONFIGURAR > ADAPTAR > CRIAR` continua a regra.

## O que é nosso

- autoridade humana invariável;
- Creative e Canonical separados;
- promoção para Canonical apenas por Human Gate;
- IA/provider com autoridade zero;
- PASS / FAIL / UNKNOWN;
- proveniência direta e inversa;
- contradições preservadas;
- eliminação automática apenas para duplicação absolutamente exata;
- agentes como microprocessos reconstruíveis: tiny + prompt + contexto + regras + ferramentas permitidas + schema + objetivo;
- experiência validada pode tornar-se processo/template reutilizável;
- ferramentas e bancadas substituíveis;
- desmontar deve ser tão fácil como montar.

## Contratos e processos

O runtime candidato executa processos Python validados. O esquema abaixo conserva a proposta histórica de templates; `process.yaml` não é uma dependência do executor atual:

```text
process.yaml
input.schema.json
output.schema.json
prompts/
rules.yaml
tests/
```

Se o processo é conhecido, executa-se com o mínimo de IA. Se não é conhecido, a bancada ajuda a descobrir/decompor; o resultado só se torna template reutilizável depois de testes e aprovação humana.

## Prova mínima

1. linguagem natural na Folha;
2. routing pelo Kernel;
3. tarefa cognitiva enviada à bancada Open Notebook/tiny;
4. resultado JSON válido;
5. gravação em Creative;
6. tentativa de escrita direta em Canonical bloqueada;
7. Human Gate permite promoção explícita;
8. destruir/reconstruir bancada sem perder memória Nexus;
9. recuperar proveniência do resultado até ao pedido/fontes;
10. repetir tarefa semelhante e medir reutilização do processo.

Esta lista é um critério de aceitação, não uma declaração de que todos os percursos estão comprovados. Consultar a evidência por capacidade no ponto de situação.

## Benchmark externo único

Para evitar dispersão, o projeto externo de comparação escolhido em 30-09-2026 é **Negentropy-Laby/OpenDoge**. Não é dependência do Nexus nem modelo a copiar. Serve apenas para aprender e falsificar decisões: local-first/single-operator, workflow templates, contracts, approvals, evidence/replay e slots/capabilities substituíveis. O Nexus mantém a sua redução própria: Folha única, memória soberana exterior à IA, Open Notebook apenas como bancada descartável e aprendizagem processual sem crescimento de autoridade.

## Regra permanente

- **LIGAR > CONFIGURAR > ADAPTAR > CRIAR.**
- **NENHUM COMPONENTE ENTRA SEM UM FAIL QUE O JUSTIFIQUE.**
- **SE NÃO PODE SER DESLIGADO SEM DESTRUIR O RESTO, ESTÁ MAL INTEGRADO.**
- **MEMÓRIA NÃO É AUTORIDADE.**
- **IA NÃO É AUTORIDADE.**
- **PROMOTE_TO_CANONICAL só acontece após decisão humana.**
- **Similaridade nunca autoriza eliminação; apenas duplicação exata.**

## Licença do projeto

Código/documentação próprios: PolyForm Noncommercial 1.0.0. Dependências mantêm as suas próprias licenças; antes de redistribuição devem ser fixadas versões e `THIRD_PARTY_NOTICES`.

[Estado operacional](nexus/docs/PONTO-DE-SITUACAO.md) · [Arranque](nexus/README.md) · [Constituição](CEREBRO_CONSTITUTION.md) · [Arquitetura e genealogia](CEREBRO_ARCHITECTURE.md) · [Decisões](DECISIONS.md)

Os documentos conceptuais e planos datados preservam etapas anteriores (incluindo Activepieces/Conductor); a composição executável atual deve ser conferida no código, na PR #23 e na evidência por SHA. A organização documental não altera as invariantes M1–M14.
