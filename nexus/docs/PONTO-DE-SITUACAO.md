# Nexus — ponto de situação atual

## Laboratório Writer isolado — 08-10-2026

Loop de resolução retomado por instrução humana em 09-10-2026. Goal ativo:
procurar solução reproduzível e validar integralmente antes de preencher proposta.
Último ensaio Writer 37900791913: duas rotas FAIL aos 45 s, canary IPC PASS,
Jobs finais zero. LPAC confirmado independentemente nos dez eventos observados
por AccessCheck num descritor em memória; conta não elevada, mesmo Job/capabilities.
O leitor MSAA teve CO_E_NOTINITIALIZED; COM corrigido apenas no leitor externo,
execução real dessa correção ainda NOT RUN. Run 37901277588 parou antes de
Writer: PDB oficial tem GUID correto, mas age PDBI 3 versus PE 2. Correspondência
recusada; a semântica do validador Microsoft está em investigação.
Resultado B abaixo é história da fase anterior, não encerramento deste loop.

Retoma humana confirmada: não houve reposição; este chat é do laboratório Writer.
Fase histórica concluída como diagnóstico sem solução (B): run 37840879467,
2 FAIL/45 s e canary PASS. Conta normal, runtime original, Jobs finais zero.
O leitor CDB foi corrigido e validado num helper; pilhas reais indicam espera
em diálogo/message loop (LIKELY). SALFRAME LibreOffice 26.2 visível; consulta
de etiquetas sem texto disponível. Causa exata NOT PROVEN; não declarar Nexus resolvido.
Proposta mínima vazia, Folha e regressão de solução NOT RUN; loop atual ativo.
ProcDump rejeitado por auto-review por possível exposição de dados sensíveis:
NOT RUN. Usados somente rastreios/texto/captions, sem memória bruta.
Provas e tentativas do leitor persistidas em lab-evidence; principal intacto.

Esta entrada aplica-se **apenas a PAPACREATOR/nexus-writer-lab**. O estado Nexus
abaixo é história congelada do SHA b4d50ab8469cf60dfa3228c7c34ef9a1285ac827.
Pedido humano: laboratório separado, baseline exato, matriz de uma variável,
evidência IPC e regressão antes de qualquer proposta; nunca alterar o principal.

Proveniência: commit inicial 3f4e085 (apenas SOURCE_BASELINE.md, parent exato).
Código Host/Store/Kernel/sandbox original intacto. lab/ e workflows adicionais
guardam observações externas e variantes de flags em cópias descartáveis.
Relatórios próprios na raiz foram expressamente pedidos para este laboratório.

Workflow original 37813977363: 2 FAIL/5 PASS, Writer timeout 45 s nas duas rotas,
legacy pipe WinError 5/LOCAL permitido. O pacote baixou 26.2.6.3; esse resultado
não substitui o build original. Matriz 37814878330 em aa14ad8 usa instalador
arquivado 26.2.6.2 e hash oficial. A confirmou o timeout antes de B–G.
ETW e Procmon revistos e evidência focalizada persistida. Fonte do mesmo tag contradiz a hipótese de UserInstallation
mudar o prefixo legacy para LOCAL; causa efetiva do timeout permanece NOT PROVEN.

PC local: Windows 11/26200, LO 26.8.0.3; probe IPC PASS, rotas BLOCKED antes de
Writer por falta de direito para preparar DACL. Não ampliar permissões.
Diagnóstico encerrado (resultado B): A–G falharam; alternativa I também falhou
na conta normal. Causa NOT PROVEN; não declarar Nexus resolvido.
Sem solução PASS, regressão 100+100 ainda NOT RUN e proposta mínima vazia.
Ver ../../LAB_REPORT.md, ../../RESULT_MATRIX.md e ../../TRACE_EVIDENCE.md.

## Convergência técnica Work — 08-10-2026

Pedido corrente: convergir a PR #32 num único produto Windows, seguindo #31, #32, #34 e #33. Work altera código/testes e regista operação; a PR #34 conserva arquitetura/documentação/auditoria. Os relatórios datados abaixo continuam como história; não validam o HEAD corrente.

Candidato único: [PR #32](https://github.com/PAPACREATOR/cerebro-parvo-/pull/32), branch `cleanup/llamacpp-only-20261007`, base `lab/windows-full-install-20261006` (`90683cd3744db074c4ea3b3c170aad6218f2b8ed`). Último SHA de código/diagnóstico registado nesta atualização: `a7bc403091d628db1af802b2cf8c496d6f78e055`. O HEAD exato e a matriz concluída de workflows devem ser conferidos no comentário de continuação da PR: um novo commit exige repetir todos os gates aplicáveis. **Sem PASS global enquanto existir um FAIL ou gate por executar. Sem merge em main.**

`main` observado: `2033ff25c37786a5e0853d894cc31514659c7d8a`. PR #31: `628359cb4dfc363734894e0724eba25fb164acd8`; PR #34: `2c91ad036f94c03777183d60b4c977a4ee9dc68e`. Nenhuma PR sucessora encontrada na recuperação de 08-10. #31 fornece genealogia dos contratos transacionais; não foi transplantado outro Kernel. Os apontamentos CodeQL dessa PR sobre `Path`/`tmp_name` não usados permanecem documentados como dívida estática histórica, sem FAIL funcional que justifique tocar nessa implementação.

### Ciclos e provas por SHA

| Alteração | FAIL preservado e correção mínima | Evidência |
|---|---|---|
| Startup, `5a0559c` | Dois testes interceptavam os.replace embora Windows publique por _replace_durable/MoveFileExW. Passaram a observar e falhar na fronteira durável real; bytes antigos/novos completos e ausência de temporários mantidos. Runtime intacto. | Seis workflows então aplicáveis SUCCESS no mesmo SHA: auditoria, compatibilidade, crash, confinement, Windows, Integration. [Windows 37770378941](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37770378941); [Integration 37770378926](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37770378926). |
| Contratos, `4b89dd0` / `6d96a96` | A/B das dez capacidades, morte real antes/depois da publicação Canonical, consistência e bootstrap funcional. Peer CLI inicial exigia leitura de uma pasta Windows protegida; substituído por PE C nativo, sem essa concessão. | FAILs e relatórios nos comentários #32. Peers não provam instalações reais de Java/Writer/modelos. |
| Binding, `2c928f7` | Bootstrap: 3 FAIL/5 PASS antes; launcher com Git real: 8 FAIL/8 PASS antes. Autorização explícita, SHA/origin/checkout limpo, binding externo expected_head, BOM PowerShell e renovação explícita. | Launcher 16 PASS após; bootstrap 8 PASS em cada Windows. Mantidos helpers/entrada existentes; bundle completo opcional. |
| Stdio LPAC, `5ae70d2` | A/B expôs PermissionError: nul em Java/Writer. Pipe/EOF vazio substituiu DEVNULL, conservando prazo, erro e kill da árvore. | Mesmos resultados/bytes passam; selo atualizado só para adapters afetados. Nenhuma concessão ao NUL global. |
| A/B, `80976b5` | Redução medida sem presumir um único processo adicional: A/B 4/2 nas rotas Python, 6/4 nos peers CLI. | [Confinement 37777486939](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37777486939): 31 PASS por Windows. [Writer 37777486997](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37777486997): timeout real no Host/LPAC; PASS global recusado. |
| Via direta, `7fe89c3` | Três contratos FAIL-first: importação MCP obrigatória, segunda sandbox no runner e dependências core. Após A/B verde, B passou a ser o runner selado. | Local 94 PASS/20 gates Windows NOT RUN. A/B 10/10; novo Host completo 8/10, dois FAILs PDF; [Confinement 37780160271](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37780160271). |
| Diagnóstico, `a7bc403` | Binding estrutural residual procurava pin MCP no core; corrigido mantendo o critério em requirements-mcp. Diagnóstico limitado dos FAILs Host e probe nativa IPC Writer. | Contratos locais afetados 10 PASS. Novo SHA exige nova prova. XML Writer preservado também em FAIL. |

Contagens de funções, operações e inputs não são somáveis: suites sobrepõem-se e repetições por OS/SHA não acrescentam inputs distintos. Morte de processo não equivale a corte de energia/disco físico.

Correção seguinte dos peers: o diagnóstico em a7bc403 mostrou WinError 5 ao consultar soffice.com. A fixture colocou o executável diretamente numa pasta pytest privada, pelo que a raiz de leitura calculada era o diretório pai de pytest. O peer passa ao layout LibreOffice/program, com a raiz própria esperada pelo adapter. Apenas teste alterado; ACL/token/Host/Store conservados. Repetição nativa PENDENTE neste commit.

Auditoria do SHA efetivamente testado: os logs de checkout mostravam refs/pull/32/merge e um SHA de merge sintético, mesmo com os runs associados ao HEAD candidato. Os oito workflows passam a fixar ref no pull_request.head.sha (ou github.sha fora de PR). A repetição seguinte verifica o próprio commit candidato; os resultados anteriores ficam associados aos seus runs/árvores, sem serem transferidos ao novo SHA.

Atualização de provas em a2d76ff: confinement concluiu nos dois Windows, incluindo 41 PASS por job (A/B + dez capacidades Host/Human Gate/Canonical/restart) e bootstrap 8 PASS. Windows 2022 precisou de repetição por timeout de vswhere antes dos peers; log original conservado, limites intactos. Writer instalado repetiu 2 FAIL/5 PASS. Legacy pipe foi recusado com WinError 5, LOCAL funcionou; a fonte 26.2.6.2 usa legacy. O ponto interno preciso do timeout continua inferência, não rastreio completo.

Regressão Windows: Core 140, Blocks 1079 e Practical 79 PASS; suite completa interrompida pelo limite do job de 15 min após 1525 PASS/12 SKIP. CANCELLED não é PASS. As suites passam a jobs separados com os mesmos comandos/limites, sem retirar testes. Novo HEAD exige repetir os oito workflows antes da matriz final em #32/#33.

Continuação em `d7798a4`: auditoria, CodeQL, crash/recovery, compatibilidade, confinement nos dois Windows e os seis jobs de integração concluíram SUCCESS. Confinement repetiu os 41 testes nativos por OS. Writer repetiu 2 FAIL/5 PASS; limites/fronteira intactos. A regressão standard isolada também foi CANCELLED aos 15 min, após 1530 PASS/12 SKIP (interrupção observada em ssl.py, sem prova de FAIL funcional). [Run e XML preservados](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37785435070).

Correção apenas da distribuição CI: os mesmos 64 módulos standard são enumerados e repartidos por índice par/ímpar em dois jobs Windows. União = 64, interseção = 0; as seis exclusões de volume existentes mantêm os gates dedicados. Não se reduz cobertura nem se aumenta prazo. Log por teste, vinte durações e XML por partição permitem localizar uma eventual demora individual. Novo HEAD deve repetir os oito workflows; o PASS de uma partição não valida a outra nem o Writer.

### Runtime e redundâncias justificadas

A Folha conserva dez processos explícitos da política. **Front Door natural/tiny com sete intenções: NOT INTEGRATED**; não existe mapa 7→10 aprovado nesta convergência. A seleção explícita é o protótipo autorizado; não foi inventado router novo.

Host é o único dono de launch/LPAC/AppContainer SID/Job/deny roots/timeout. O runner faz dispatch fixo para adapters existentes, recusa execução Windows fora dessa fronteira, valida JSON/schema/bytes e devolve `nexus/python-direct`. Não há modelo, rede ou segredo no filho; o broker confiado entrega snapshots delimitados. Fingerprint continua fixado antes da execução e verificado pelo Store. Alterar runner muda o fingerprint; pedidos pendentes antigos exigem reconciliação explícita. Canonical comprometido é verificado sem repetir ferramentas.

Retirados da via interna: relay cliente/servidor MCP, importação obrigatória do SDK e segundo dono de sandbox execute_confined. MCP externo, ferramentas e testes reais de protocolo permanecem; baseline A só em `tests/_mcp_baseline.py`. `requirements.txt` contém jsonschema; `requirements-mcp.txt` fixa MCP/trio; requirements-test inclui ambos. Preparar o core instala dependências de teste para executar gates; MCP não é importação necessária ao runtime.

Mantidos: SHA-256 Windows CNG + Python/hashlib independentes; selo Host e binding externo ao Git; validações independentes runner/Store/UI/policy/schema; bytes originais e proveniência inversa; Creative/Canonical separados; HumanDecision ligada ao hash; atomicidade Windows WRITE_THROUGH e crash/restart/idempotência. PS/.NET é diagnóstico externo, sem substituir CNG. **Host/Store, M1–M14 e lógica do Kernel não foram alterados.**

Ficheiros centrais: adapters/runner.py, languagetool.py, office.py, integrity.json e requirements; windows/bootstrap-nexus-local.ps1, sync-nexus-code.ps1, nexus-launcher.py e binding no instalador completo; testes startup/A-B/consistência/crash/dependências/bootstrap/launcher/Writer e workflows. História de FAILs e candidato A/B preservada no Git/GitHub.

### Entrada humana e limites

Na raiz de checkout oficial, depois de conferir o SHA candidato:

```powershell
$accepted = git rev-parse HEAD
powershell.exe -NoProfile -File nexus/windows/bootstrap-nexus-local.ps1 -RepoRoot (Get-Location).Path -ExpectedHead $accepted -AuthorizePrepare
```

Bootstrap core existente: confere origin, Git limpo e HEAD esperado, reutiliza preparação/inventário/plano e copia launcher para fora do repositório com expected_head. Nexus.lnk usa esse binding; HEAD diferente ou ficheiros alterados recusam arranque. Aceitar atualização exige repetir bootstrap com novo SHA explícito. Não executar preparação como se os FAILs atuais fossem release aprovada.

Instalador completo/bundle cerca de 70 GiB é opcional e dependente da aceitação física; não foi executado. Provisioning protegido, modelos/GPU, contas/serviços/perfis Windows e PC de Pedro: **NOT RUN**. CI usa runners descartáveis e dados sintéticos.

### Bloqueios e continuação

PDF pelos peers no novo Host passou a repetição completa em a2d76ff após corrigir a fixture; LibreOffice 26.2.6 instalado excede 45 s dentro da fronteira existente, embora Writer fora dela passe. Stdout/stderr Writer vazios em 7fe89c3, sem PDF/proposta promovida. IPC Win32 incompatível com AppContainer é hipótese; a observação legacy/LOCAL deve ser confrontada com binário/fontes da mesma versão antes de atribuir causa.

Próximo ciclo: fechar a regressão repartida e toda a matriz no mesmo HEAD, manter Writer a falhar enquanto não existir solução equivalente dentro da fronteira aprovada; repetir auditoria, sintaxe, unitários, integração/stress, segurança, crash/recovery, bootstrap/launcher e E2E no mesmo HEAD. Registar matriz e bloqueios reais em #32 e #33. Nenhum prazo/permissão aumentado para fabricar PASS.

## Atualização documental e capacidades — 06-10-2026

- Constituição e arquitetura ativa reconciliadas com Kernel/Host/Store + MCP;
- Activepieces/Conductor/Spiff preservados como genealogia, não runtime;
- planos/instalação/matriz de compatibilidade atualizados;
- F001–F008 e F011–F013 marcados com interpretação atual sem apagar evidência histórica;
- LibreOffice atual continua limitado a DOCX/ODT → PDF;
- Writer editorial completo passou a ter contrato próprio em `CAPABILITY-WRITER-EDITORIAL.md`, ainda **NOT IMPLEMENTED**;
- arquitetura M1–M14 não foi alterada.

Este é o único documento de estado operacional corrente em `nexus/docs`.
Estados antigos, filas, handoffs e quadros temporários foram removidos da árvore ativa; continuam recuperáveis pelo histórico Git e pelos PRs/comentários.

## Relatório corrente — 06-10-2026

Pedido humano: corrigir e testar sem alterar a estrutura, e escrever o ponto de situação. **Protótipo funcional integrado e validado no CI em e579af5; provisioning não protegido recusado; instalação protegida e aceitação no PC ainda por concluir.** Arquitetura M1–M14, responsabilidades Kernel/Host/Store, Creative/Human Gate/Canonical e caminhos existentes preservados.

Runtime com gates Nexus/Host/MCP/Avatar e recusa de provisioning confirmados: `e579af5f599942efe717142936ba8f611c19b969`. Esta atualização final altera só este relatório; o código testado permanece igual. PR #23 draft, branch lab-open-notebook-avatar-20261004. Baseline/base e main não foram promovidas.

| Bloco | Números observados | Resultado/evidência |
|---|---|---|
| Windows Server 2022 e 2025, fronteira nativa | **10.000 operações filesystem recusadas**, zero ERROR; cofres sintéticos, HKCU, loopback disponível e filho DENIED; trabalho atribuído funciona | **PASS**, [run 37444721963](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444721963) |
| Autoridade Host/Store | **10.000 inputs**, quatro famílias de 2.500, sem dados alterados nem aprovação forjada | **PASS**, mesmo run |
| Host real | 22 alvos proibidos DENIED + dois controlos positivos | **24 PASS**, mesmo run |
| Retorno e recuperação | 76 funções/contratos | **76 PASS**, mesmo run |
| Hash independente CNG | Sete vetores, incluindo vazio, NUL, Unicode, chunk e 2 MiB | **PASS**, mesmo run |
| Concorrência | 500 substituições atómicas com quatro leitores | **PASS**, mesmo run |
| Listagem de dependências | Pasta listável, ficheiro selecionado legível, outro ficheiro DENIED e DACL original intacta | **PASS**, mesmo run |
| Provisioning | **18 critérios PASS** por OS: nove com sentinelas e nove invocações reais sem sentinelas; flags não contornam a recusa | Mesmo run; recusa, não instalação funcional |
| Regressão Nexus completa | **1.386 PASS**; Core 140, Blocks 1.068 e Practical 40 também PASS | [Windows 37444722019](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444722019) |
| MCP real e OpenNotebook | **1.000 chamadas MCP reais + inventário 33 tools**; A–G PASS, regressão 1.386 PASS | [Integration 37444721856](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444721856) |
| Avatar | **Windows 168 PASS, zero SKIP** em 97,73 s; Linux 165 PASS, três critérios só Windows não aplicáveis; timeout 1,86 s < 3 s | [Run 37444721936](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444721936) |

Não somar estas linhas: funções pytest, inputs e operações são unidades diferentes, e as suites sobrepõem-se. Repetição por OS ou por SHA não aumenta o número de inputs distintos.

Correções implementadas: validação ASCII da sessão; launcher Windows com LPAC/DACL/Job e ausência de fallback; snapshot privado separado do Store; stdio MCP em pipes LOCAL/eventos sem rede; CNG para verificação independente; avatar Windows ligado ao launcher existente para codecs, PIL e worker. O conflito de dependências no CI Avatar foi corrigido instalando apenas o jsonschema consumido pelo selo do Host nesse ambiente; as versões Nexus permanecem fixadas.

O Host limita os processos que lança. Os ensaios não são uma auditoria de todo o Windows nem confinam retroativamente OpenNotebook/ACE/Forge ou outros backends já iniciados fora desse launcher. Modelos/GPU, instalação protegida no PC e limpeza de perfis/ACL em crash: **NOT RUN/PENDENTES**. A inferência aprendida é substituída nos contratos Avatar deste run. Os instaladores Windows, o setup global histórico e o provision de modelos recusam antes de efeitos enquanto a instalação protegida não está implementada. O ambiente já instalado continua testável por check-nexus.ps1.

PC de Pedro, contas, serviços, políticas e ficheiros pessoais não foram alterados. Nenhum PASS de CI é convertido em perfeição universal, instalação física ou release. Etapa atual concluída no repositório: corrigir o âmbito/arranque Avatar, comprovar recusa do provisioning e fechar regressão. Próximo trabalho pendente: provisioning protegido, limpeza após crash do Host e aceitação de modelos/GPU no Windows real. Não executar os instaladores bloqueados como se fossem PASS.

Microcontrato Avatar/Host, 06-10: FFmpeg/ffprobe só necessitam de leitura do diretório do executável e dependências selecionadas; não devem ler o Python/Nexus do Host. Em cc3d1be, [run 37437120425](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37437120425), o FFmpeg real copiou o input atribuído mas também leu Lib/this.py fora do trabalho: **1 FAIL em 37,85 s**; regressão Windows seguinte NOT RUN por esse FAIL. O job anterior de 48a7215 foi CANCELLED no limite de 20 min, sem XML final; não é PASS e a causa desse tempo não está provada. Correção mínima neste commit: codecs recebem apenas diretório do executável e dependências explícitas; só processos Python recebem os caminhos Python/Nexus necessários. Nenhuma alteração de estrutura, capacidade de rede, token, Job ou portão humano. Em b3752b3, [run 37438100330](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37438100330), o mesmo contrato Windows passou: leitura atribuída funciona e a leitura do Host é recusada. Suite completa ainda em curso. Dado o CANCELLED anterior, o CI passa a executar o teste de timeout existente no início e a conservar nomes/durações; não aumenta limites nem enfraquece testes.


Microcontrato de timeout Python, 06-10: em 2f39016, [run 37438868791](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37438868791), o mesmo FFmpeg PASS em 0,15 s, mas o teste existente de timeout terminou em 18,99 s, acima de três segundos: **1 FAIL / 1 PASS**, regressão Windows seguinte NOT RUN. Não aumentar o limite do teste. Correção deste commit: o launcher distingue leitura do diretório sem herança da leitura dos descendentes; Python recebe ficheiros/DLLs e biblioteca padrão, com pacotes externos só quando selecionados. PIL recebe apenas PIL e a sua dependência XML presente; os pacotes do modelo são explícitos no worker. O worker lê os ficheiros Nexus necessários à verificação da fronteira, sem concessão recursiva de todo o Nexus. O import jsonschema passa para validate: inspecionar o token não deve carregar o validador de dados nem exigir os seus pacotes. Selo atualizado para os dois ficheiros core alterados. Um controlo nativo exige listar uma pasta, ler um ficheiro selecionado e recusar outro ficheiro na mesma pasta. Sem alteração de estrutura, rede, token, Job, limites ou decisão humana. Repetição dos quatro critérios Avatar iniciais, regressão integral e gates Nexus: **PENDENTES**.

Repetição em 722814e, [Avatar 37440409335](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37440409335): **1 FAIL / 3 PASS**. Timeout 45,54 s; pipeline de vídeo/retorno/idempotência PASS, worker direto recusado e worker confinado --help PASS, leitura FFmpeg não atribuída recusada. A restrição funcional passou mas a tentativa não resolveu a demora; não ocultar o agravamento. [Confinamento 37440409636](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37440409636): ambos Windows PASS, incluindo novo contrato de listagem sem leitura, 10.000 operações recusadas, 10.000 inputs, Host 24 e retorno 76. Correção seguinte usa SetSecurityInfo por handle MAXIMUM_ALLOWED só para diretórios sem herança, também na revogação. É o comportamento documentado que evita propagação aos filhos, sem proteger/desproteger DACL humana nem dar o handle ao filho. Concessões recursivas mantêm SetNamedSecurityInfo. O controlo acrescenta DACL do ficheiro não atribuído intacta. Fonte primária e alternativa escolhida: [Microsoft SetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo); SetFileSecurity obsoleto e SetKernelObjectSecurity para objetos de filesystem foram descartados. Selo nativo atualizado; timeout de três segundos e regressão mantidos, repetição PENDENTE.

Repetição em 7726709, [Avatar 37441690692](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37441690692): **Windows 168 PASS, zero SKIP, 63,93 s**; quatro critérios iniciais PASS em 5,32 s. Timeout **1,74 s < 3 s**, pipeline/retorno/idempotência 2,25 s e worker nativo 0,74 s. Linux 165 PASS, três critérios exclusivamente Windows não aplicáveis. [Confinamento 37441690714](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37441690714), [Nexus Windows 37441690741](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37441690741) e [Integration 37441690748](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37441690748): SUCCESS. A distinção de ACL ficou testada e a demora anterior foi resolvida sem aumentar permissões, timeout ou limite de CI.

Próximo microcontrato, dono Host, 06-10: provisioning não validado deve recusar antes de diretórios, processos, instalação, downloads ou conta global, incluindo flags de salto. Entradas revistas: os três instaladores Windows, o descarregador de modelos (CLI/função) e setup-isolation.ps1 histórico, que ainda podia criar conta/pastas globais com elevação. Este commit acrescenta primeiro nove critérios com os entrypoints reais e sentinelas de side effects; fonte ainda sem alteração. As sentinelas impedem a alteração global no ensaio, e não constituem prova de confinamento. Baseline esperada FAIL, resultado PENDENTE. Após recusa incondicional, repetir com e sem sentinelas: só isso prova recusa real, não instalação funcional. Estrutura preservada e implementação histórica retida; nenhum script físico executado no PC de Pedro.

Regressão do runtime 7726709 em 6ba7ea7 (só testes/documentação), [Avatar 37442921072](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37442921072): primeira chamada timeout **3,64 s > 3 s**, vídeo/retorno/idempotência PASS em 1,85 s, worker nativo PASS e FFmpeg restrito PASS; **1 FAIL / 3 PASS**. O primeiro PASS de 1,74 s não é prova de estabilidade do arranque. Os imports Nexus e a ligação de protótipos DLL passam para a inicialização do serviço, sem criar tarefa, perfil, processo ou ACL. O selo continua verificado em cada chamada e não há fallback. O mesmo limite de três segundos e a suite integral mantêm-se; repetição PENDENTE.

Baseline provisioning, [Confinamento 37442920985](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37442920985): **9 FAIL** em Server 2025, sentinelas observadas em New-Item, Get-Command, Resolve-Path, Read-Host e mkdir do descarregador. Original e pasta não criada invariáveis. Outros gates Native/Host/retorno PASS. Falha esperada do contrato, não nove ataques bem sucedidos no PC. A mesma recusa deve ser comprovada depois sem sentinelas.

Contenção do provisioning, 06-10: os três instaladores e o setup histórico recusam imediatamente, antes de resolver caminhos, perguntar credenciais, criar pastas, instalar ou lançar programas. O descarregador recusa no início de provision em Windows, cobrindo CLI e função, antes de gdown, mkdir ou HTTP. Flags de salto não contornam o bloqueio; nenhuma criação de conta global nem política adicional. Fonte histórica preservada sem execução e caminhos inalterados. Repetição com as nove sentinelas originais e nove invocações reais sem sentinelas = **18 critérios PENDENTES**. Isto implementa recusa segura; **não implementa nem aprova instalação protegida funcional**. check-nexus.ps1 continua disponível para um ambiente já instalado. Correção do arranque Avatar em validação simultânea, com o teste <3 s mantido.

Fecho desta etapa, 06-10, e579af5: [Confinamento 37444721963](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444721963) SUCCESS nos dois Windows: 10.000 operações DENIED/zero ERROR, 10.000 inputs PASS, 24 Host PASS, 76 retorno PASS, sete vetores CNG PASS, ACL do ficheiro não atribuído intacta e **18 recusas PASS** (6,36 s em 2025; 7,56 s em 2022). [Windows 37444722019](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444722019): Core 140, Blocks 1.068, All **1.386** em 229,15 s, Practical 40 e wrapper PASS; erro de prerequisites é controlo negativo deliberado. [Integration 37444721856](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444721856): A–G PASS, MCP real 1.000/inventário 33, regressão **1.386** em 234,98 s. [Avatar 37444721936](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37444721936): Windows **168 PASS**, Linux 165 PASS com três critérios Windows não aplicáveis; primeira chamada timeout **1,86 s < 3 s**. O mesmo ajuste de arranque passou antes em 2c53611, timeout 2,40 s e Windows 168 PASS. Auditoria SUCCESS. Não somar repetições, OS, inputs, operações e funções. Nenhum modelo aprendido/GPU real é coberto pela substituição do modelo usada nestes contratos.

Resultado: há um núcleo funcional e uma extensão Avatar tecnicamente validada como protótipo. Falhas de leitura ampla e propagação de ACL foram corrigidas; a inicialização deixa de pesar na primeira chamada temporizada, sem autoexecutar ferramenta. O provisioning não validado está contido por recusa real, inclusive chamada direta do descarregador e setup que criava conta global. Uma recusa segura não equivale a instalação funcional. Estrutura e M1–M14 preservados; Human Gate continua obrigatório; nenhuma alteração no PC de Pedro, merge ou release. Este commit de fecho modifica somente o relatório, e conserva toda a sequência FAIL/correção/PASS abaixo e acima.

## Fonte de verdade operacional

- PR ativa: **#23 — CURRENT BASELINE**.
- Branch de continuação: `lab-open-notebook-avatar-20261004`.
- Kernel/Host/Store são a autoridade do sistema.
- MCP é transporte determinístico.
- OpenNotebook, LanguageTool, LibreOffice, ACE-Step, Forge e restantes integrações são ferramentas externas.
- Creative precede Canonical.
- Promoção para Canonical exige decisão humana explícita.
- Tiny/IA não recebe autoridade de sistema.
- Duplicação exata é a única base para eliminação automática; semântica/similaridade apenas sinaliza revisão.

## Correção e 10.000 ataques — implementação em validação, 05-10-2026

Pedido humano: resolver e testar 10.000 casos. Contrato do microprocesso, dono Host (sem alterar M1–M14): lançar somente um comando selecionado pelo Host, com inputs delimitados, identidade Windows de tarefa, direitos de leitura dos executáveis e escrita no trabalho, sem direitos sobre Kernel/cofres/dados externos nem capacidades de rede. Criar suspenso; verificar token AppContainer, SID e associação ao Job antes de retomar. O Job termina descendentes e impõe limites. Erros nativos não autorizam fallback. ACLs da identidade de tarefa são revogadas na limpeza sem restaurar/destruir ACLs humanas completas.

USE/ADAPT: mecanismos oficiais AppContainer/SECURITY_CAPABILITIES, DACL e Job Object, chamados por ctypes; sem serviço/conta/administração global novos. A fronteira nativa começa isolada e a ligação ao Host/MCP é feita apenas no candidato draft; não promover uma baseline sem os gates completos. Avatar/instaladores externos são um âmbito separado que também precisa de portão nativo. O teste executa 10.000 operações reais de ficheiros, leitura dos dois cofres sintéticos, descendente, controlo de escrita permitida e tentativa de ligação a um socket loopback realmente disponível. ERROR/timeout/não execução não contam como DENIED. Fontes: [Microsoft AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

Estado desta etapa: **HOST/MCP/CNG NATIVOS PASS NO CI / AVATAR EM REPETIÇÃO / INSTALAÇÃO PENDENTE / SEM RELEASE**. O gate Host e os sete vetores CNG passam nos dois Windows; os FAILs históricos abaixo são conservados. A aceitação exige comprovar fronteira nativa, gate do Host real, retorno/reinício e regressão no mesmo código. PC de Pedro não foi alterado.

Primeiro ensaio nativo, commit efc5b0e, [run 37364869364](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37364869364): 1 FAIL / 1 PASS. O SID derivado sem perfil não permitiu CreateProcessW (erro 2); os 10.000 ataques não executaram. Corrigida a preparação para perfil efémero por tarefa, com acesso da ferramenta ao armazenamento desse perfil explicitamente negado e limpeza no fim. A pasta de trabalho continua a ser o único destino de filesystem atribuído. Isto não cria uma conta Windows nem dá direitos globais à ferramenta. Repetição obrigatória, ainda sem PASS.

Correção de autoridade: Host.authorize agora exige str ASCII antes de hmac.compare_digest; sessões Unicode falsas passam a Blocked. O método real extraído por AST passou controlo válido + 10.000 sessões inválidas localmente; é prova de componente, não importação completa do Host. Novo test_authority_10000.py testa o Host/Store completo em quatro famílias de 2.500 inputs (sessões, tickets humanos forjados, autoridade em resultados e processos não registados), com snapshots de dados invariantes. Manifesto atualizado para a alteração revista. CI pendente. Os 40.000 inputs antigos preparados noutra cópia continuam NOT RUN; não são estes testes.

O gate Windows passa a testar Windows Server 2022 e 2025 separadamente, sem fail-fast, conservando artefactos por plataforma e os critérios do gate Host. O job 2025 do commit f5596d4 ainda estava em fila sem runner na última consulta; fila não é PASS nem FAIL do código.

Commit 7aed704, [run 37367782434](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37367782434): **10.000 inputs de autoridade PASS em cada Windows** (4 funções pytest; 2.500 casos por função), 1,03 s em Server 2022 e 0,85 s em Server 2025. A fronteira nativa continuou 1 FAIL / 1 PASS por OS: CreateProcessW erro 203 (variável de ambiente não encontrada), antes dos ataques. Nova preparação acrescenta USERPROFILE/APPDATA/LOCALAPPDATA/HOME com valores da área de tarefa, sem herdar o perfil humano. A hipótese de ambiente só passa a causa resolvida após repetição. Gate Host ainda 22 acessos proibidos permitidos; integração continua pendente.

Commit c91ba66, [run 37368326605](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37368326605): o ambiente corrigiu o lançamento; as 10.000 operações realmente executaram. Resultado do teste ainda FAIL: 6.000 recusas Win32 e 4.000 PermissionError sem winerror, classificadas como ERROR; escrita permitida funcionou, rede deu timeout. Nova verificação aceita apenas ACCESS_DENIED Win32 ou errno EACCES/EPERM sem winerror, conserva canários e exige diagnóstico nativo de capacidade de rede em falta, com socket disponível antes/depois. Timeout isolado continua ERROR. Acrescentado alvo sintético com ALL APPLICATION PACKAGES e LPAC opt-out para que esse direito partilhado não alargue a tarefa. A criação exige sucesso do atributo oficial LPAC; token AppContainer/SID/Job são verificados antes de retomar e o efeito LPAC é testado contra o alvo ALL APPLICATION PACKAGES. Resultado pendente neste novo SHA.

Commit adb64f2, [run 37370018066](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37370018066), Server 2022: FAIL antes de retomar. GetTokenInformation classe 46 deu ERROR_INVALID_PARAMETER (87). O header contém a classe, mas isso não prova suporte Win32; removida essa consulta como pré-condição. Mantidos atributo de criação LPAC obrigatório, verificação AppContainer/SID/Job e teste comportamental do direito AAP. Nenhum ataque desse job conta como executado. Repetição pendente.

Integração preparada no candidato: Host lança runner via fronteira nativa; trabalho é snapshot numa pasta efémera separada de Store, com Store explicitamente negado à identidade da tarefa. Só Host regista estado, stdout e artefacto PDF delimitado/hash verificado após terminar o Job. Runner direto também confina. MCP direto usa stdio nativo; o filho de runner herda identidade/Job sem autorização por variável de ambiente. MCP só aceita input.bin da pasta atribuída. Java/LibreOffice diretos recusam execução fora da fronteira; descendentes mantêm os limites.

OpenNotebook: a chamada HTTP fixa e delimitada é feita pelo Host antes da validação isolada; só output/model_id/transformation_id são copiados, sem palavra-passe, sessão ou capacidade de rede. Health ACE/Forge usa o mesmo princípio para GETs fixos sem mutação. Recuperação conserva EXECUTING antes da chamada e usa resultado durável sem repetir ferramentas nem criar aprovação humana. Leitores state/list_runs passam a usar o lock dos escritores, para eliminar a corrida Windows read/os.replace; novo stress faz 500 substituições com quatro leitores (4.000 snapshots + listas), sem promover. A causa de todo PermissionError histórico não é presumida resolvida sem repetir.

O gate de 22 alvos foi adaptado apenas ao novo ponto de lançamento/pasta de trabalho: injeta o mesmo worker hostil, mantém APIs/DACL/token/Job reais, lê as observações do stdout durável e conserva os 24 critérios. Não é substituído por mocks de proteção. Duplos unitários de output/timeout e sentinelas de não reexecução apontam ao novo launcher, separados do gate nativo. Manifesto/fingerprint inclui windows_sandbox.py.

NOT RUN/PENDENTE: resultados do CI deste conjunto, perfil de crash/limpeza, instaladores/launchers externos e confinamento avatar/modelo/GPU físicos. Nenhum desses limites é substituído pelos 10.000 testes de autoridade.

Commit f01ca4a, [run 37370540374](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37370540374), Server 2022: criação/token/Job passou, mas Python terminou com 0xC0000022 (ACCESS_DENIED) sem output, antes do payload. Nenhuma operação desse ensaio conta como PASS. Implementação testa registryRead (capacidade oficial só de leitura), usada pelo arranque LPAC; não dá rede/escrita/COM. A hipótese de conceder SID RO a System32 foi retirada: o launcher deve usar as permissões de leitura de sistema já fornecidas pelo Windows, sem alterar DACLs de Windows/System32 e sem exigir direitos administrativos para isso. A verificação de token exige exatamente registryRead e recusa capacidades adicionais. Acrescentado canário de escrita no registo HKCU sintético, com original invariável. A hipótese de arranque só é resolvida depois da repetição.

Commit 59782b4, [run 37371780308](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37371780308), Server 2025: 10.000 autoridade + stress de snapshots PASS (5 funções, 8,00 s); regressão de retorno 71 PASS / 5 FAIL (arranque LPAC ainda não funcional). MCP direto revelou pasta TEMP em formato Windows 8.3 RUNNER~1 que o guard confundia com redirecionamento. O chamador passa a resolver a pasta efémera criada por si antes de a entregar; não se removem guards de symlink/junction nem se concede uma pasta externa. Gate Host não obtém observações se o payload não executa; isso continua FAIL/NOT PROVEN.

Commit 21c03d5, [run 37372670714](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37372670714), Server 2022: o Python LPAC arrancou e executou o payload; a hipótese registryRead resolve o arranque observado sem alterar System32. O gate nativo ainda FAIL por NameError no finally do socket (criação já recusada); corrigido cleanup apenas se socket existe. Os 10.000 inputs de autoridade + concorrência continuam PASS; regressão 71 PASS / 5 FAIL, com diagnóstico real ModuleNotFoundError: nexus. O pacote passa a carregar diretamente da pasta Nexus RO, sem conceder leitura/listagem ao diretório pai do repositório. Gate Host e MCP agora conservam diagnóstico limitado de arranque; nenhuma ausência de observações conta como confinamento PASS. Repetição pendente no novo SHA.

Commit 3f2f377, [run 37374094031](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37374094031): **10.000 operações reais recusadas PASS em Server 2022 e 2025**, incluindo alvo AAP; leitura Creative/Canonical, escrita HKCU sintética, socket loopback e descendente DENIED; escrita atribuída PASS. 2 funções nativas, 5,26 s em 2022. 10.000 inputs de autoridade + concorrência também PASS. Gate Host FAIL antes das observações: normalização Windows não podia ler a pasta TemporaryDirectory privada ancestral; preparação concede RO apenas a essa árvore efémera. MCP/retorno ainda FAIL: import _overlapped cria socket no próprio arranque, recusado com WSAEACCES. Nova adaptação usa AnyIO/Trio 0.34.0 e pipes LOCAL; os tipos asyncio importam, mas os seus loops são explicitamente recusados. O último probe Winsock de Trio só pode ser ignorado no código/linha observados após IOCP pronto; nenhuma capacidade de rede é acrescentada. CI desta adaptação PENDENTE; não declarar MCP funcional até PASS.

Commit f23f180, [run 37375601558](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37375601558): MCP importa e chega a Trio, mas FAIL no socketpair da fila de reentrada. Substituído esse mecanismo de notificação por evento Win32 anónimo local à tarefa, com espera cooperativa de 10 ms; sem sockets, sem capacidade nova e sem alterar o Host fora da fronteira. Gate Host continuou FAIL na normalização estrita do próprio probe; o guard agora compara cwd real com caminho canónico já verificado pelo Host e conserva o marcador de área descartável e todos os 22 alvos/critério DENIED. Não concede leitura a ancestrais humanos. Diagnóstico limitado do runner conserva a causa para a repetição. Os 10.000 ensaios nativos/autoridade continuam PASS nesse SHA; MCP/retorno aguardam novo resultado.

Commit 8f97e0f, [run 37376277120](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37376277120): **gate Host 24 PASS nos dois Windows** (22 alvos DENIED + controlos positivos); autoridade 26 PASS; 10.000 nativos e 10.000 autoridade PASS; retorno 73 PASS / 3 FAIL, limitado à verificação Windows via PowerShell dentro de LPAC. [Integration 37376277512](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37376277512): 100K Kernel PASS, 100K linguagem PASS, MCP real 1.000 + pacote OpenNotebook (33 tools) PASS (6 funções, 65,22 s), OpenNotebook/Kernel E2E 5 PASS, contrato/parse instalador PASS; health MCP 15 PASS / 2 FAIL por carregar duas vezes a configuração já ativa. Corrigida identidade do módulo bootstrap. A verificação confinada passa a usar Windows CNG/BCrypt SHA256, independente de hashlib, com provider explícito e limite 2 MiB, sem arrancar PowerShell/.NET dentro do LPAC nem conceder novas capacidades. Evidência identifica windows.cng-sha256; o backend .NET histórico permanece distinguido. Sete vetores reais nativos (incluindo vazio, NUL, Unicode e limites de chunk/input) e regressão ainda PENDENTES. Não é PASS do novo backend até repetir.

Commit 990d8cc, [confinamento 37377232938](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37377232938): 10.000 operações nativas PASS, 10.000 inputs de autoridade + concorrência PASS, gate Host 24 PASS e retorno/reinício 76 PASS em ambos os Windows. O job global ainda FAIL por um erro do novo teste: o vetor de bytes NUL recebeu o nome de ficheiro reservado Windows `nul`, em vez de um ficheiro normal. Corrigido para `nul-bytes`, preservando os bytes e as sete comparações CNG/hashlib; repetição pendente. [Integration 37377232769](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37377232769): todos os blocos A–G PASS, incluindo 100K Kernel, 100K linguagem, 1.000 chamadas MCP reais + inventário OpenNotebook, E2E, health 17 e regressão completa 1.386 PASS. [Windows 37377232851](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37377232851): Core 140, Blocks 1.068, All 1.386 e Practical 40 PASS. Contagens sobrepostas; não somar como testes distintos. Isto valida o código no CI, não a instalação/modelos/GPU no PC de Pedro.

Repetição do commit a59e447: os passos nativos/autoridade/gate Host passaram nos dois Windows; resultado global/retorno ainda em curso na publicação da etapa seguinte. Avatar Windows passa a usar o launcher nativo para FFmpeg/ffprobe, descodificação PIL e worker, com cópias de inputs, trabalho privado e dependências RO explícitas. O worker direto exige token/Job reais antes de importar o modelo; Python de inferência usa -I. Sem import Nexus/manifesto válido não há fallback sem proteção. Dois novos ensaios reais Windows verificam recusa de escrita exterior e recusa de worker direto, com controlos positivos. FFmpeg real, contratos e integração router em repetição. Modelo/GPU/PC físicos continuam NOT RUN; os ensaios substituem apenas o modelo aprendido, não o launcher Windows.

Continuação de 06-10-2026, pedido humano: corrigir e testar sem mudar a estrutura. Arquitetura M1–M14, Kernel/Host/Store e diretórios existentes preservados. Commit 7a61290: [confinamento 37378593177](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37378593177) SUCCESS em Server 2022/2025 (10.000 operações nativas, sete vetores CNG, 10.000 autoridade + concorrência, Host 24 e retorno 76). [Windows 37378593246](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37378593246) e [Integration 37378593142](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37378593142) SUCCESS. [Avatar 37378593194](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37378593194) FAIL antes de executar os testes: adicionar requirements Nexus ao ambiente upstream provocou conflito mcp==1.23.2 com fastmcp>=3, dependência transitiva de content-core. Correção mínima: instalar no ambiente Avatar apenas jsonschema==4.26.0, consumido pela verificação de integridade do Host; o launcher Windows é stdlib. Dependências/MCP do Nexus permanecem fixadas no ambiente próprio. Não usar --no-deps nem mudar o upstream para esconder conflito. Avatar real Windows/Linux em repetição; nenhum PASS do modelo/GPU físico é inferido.

## Revisão do código e segurança Windows — 05-10-2026

SHA executável revisto: `dcef003f7c3e93ed8bdfe1730ce5870f1b818e09`. A presente revisão documental não altera esse runtime. Pedido de Pedro: conferir o código real e aproveitar as proteções nativas do Windows nos bastidores, mantendo a Folha simples; não redefinir a arquitetura já fechada.

| Gate observado nesse SHA | Evidência |
|---|---|
| Nexus Windows | [SUCCESS](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37304293988): Core 140, Blocks 1068, All 1386, Practical 40 PASS |
| Integration Stress | [SUCCESS](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37304293836): blocos 100K, MCP, E2E controlado e regressão 1386 PASS |
| Avatar | [SUCCESS](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37304294007): 165 PASS em Windows e 165 em Ubuntu |
| Auditoria | [SUCCESS](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37304293869): 34 históricos e 11 de persistência PASS |
| Confinamento Windows | **[FAIL](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37304294214): 22 acessos proibidos ALLOWED; 2 controlos PASS**. Contratos de autoridade da aplicação: 26 PASS |

As contagens sobrepõem-se e não devem ser somadas. O novo Practical verde não identifica a causa do PermissionError anterior; a falha histórica continua conservada abaixo. O E2E controlado e os ensaios de avatar não substituem backend/modelo/GPU físicos completos. O gate de confinamento correu em runner Windows Server 2025, com alvos sintéticos; não é prova no PC de Pedro.

### O que o código realmente faz

- `host.py::_run` chama `subprocess.Popen` com cwd/env reduzidos e CREATE_NO_WINDOW. Não escolhe conta Nexus/token restrito, não aplica ACL e não associa Job Object. A tool mantém a identidade corrente. O gate hostil confirmou a consequência em 20 operações de escrita e 2 leituras proibidas de ensaio.
- `mcp_client.py::_open_session` usa `stdio_client` com command/args/env. A allowlist limita nomes de tools; não restringe os direitos Windows do servidor. O percurso efetivo é Host → runner → MCP → adaptador → subprocesso ou API externa.
- `adapters/office.py` e `adapters/languagetool.py` lançam os executáveis sem seleção de identidade restrita. Perfil LibreOffice por tarefa, validação de pacotes, heap Java e timeout são controlos reais, mas não isolamento de ficheiros.
- `lab/open_notebook_avatar/notebook_avatar/service.py::command` cria processos e grupos, com limites e captura de output. Não aplica a fronteira Windows do Host. O comentário do código atribui a sandbox de SO à camada externa; essa ligação ainda falta.
- `windows/sync-nexus-pc.ps1` arranca ACE-Step/Forge com Start-Process; `install-media-tools.ps1` pode usar winget e uv python install sem fixar todas as localizações/caches a ToolsRoot. Não há prova de instalação confinada; não foi executado nenhum instalador nesta revisão.
- `instance.py` e `app.py` já usam proteções Windows reais: bloqueio do diretório por msvcrt e exclusividade da porta por SO_EXCLUSIVEADDRUSE. Os gates de arranque passam; estas proteções têm âmbito diferente do isolamento de ferramentas.
- `Host.authorize` passa uma sessão Unicode diretamente a hmac.compare_digest. Ensaio do método real extraído por AST: sessão válida ACCEPTED; falsa ASCII Blocked; falsa Unicode TypeError; tipo errado Blocked. Prova de componente, sem importação/execução completa do Host. Correção local preparada não equivale a correção publicada.

### Contrato preservado e diferença de implementação

O comportamento exigido já está em [F008](F008-ISOLAMENTO-WINDOWS.md) e [Windows como hospedeiro](SCHEMAS-E-WINDOWS.md). A pessoa usa linguagem normal; Kernel/Host/Store aplicam autorização e regras; o Host lança uma tarefa delimitada; o Windows faz cumprir os direitos do processo; o Host verifica o retorno e escreve no destino permitido. A gestão de contas, ACLs, tokens e processos não pertence ao percurso normal da Folha. A pessoa continua a ver decisões humanas materiais quando exigidas.

A evidência [WINDOWS-TWO-FOLDERS](WINDOWS-TWO-FOLDERS-EVIDENCE.json), de 01-10, regista identidade Nexus, escrita permitida e leitura/escrita protegida recusadas. É válida para as duas pastas artificiais. O código atual não integra esse lançamento com credenciais no Host. Não inferir que o PC ou todas as ferramentas continuam protegidos a partir desse ensaio antigo.

**Estado: requisito definido; integração de segurança nativa incompleta; execução confinada FAIL.** Próximo microprocesso: ligar a execução real a uma fronteira Windows verificada, delimitar trabalho versus estado do Host, cobrir descendentes, acesso entre tarefas, rede e bancada/modelo; repetir o gate hostil e regressão sem enfraquecer critérios. Não é necessário redesenhar M1–M14 para reconhecer esta lacuna.

### Trabalho ainda não entregue

- Contenção de emergência e correção de sessão Unicode: preparadas numa cópia local separada, **não publicadas nem validadas no CI**. O HEAD publicado continua a executar como antes. Bloquear execução seria contenção, não PASS de sandbox funcional.
- 40.000 inputs adversariais adicionais: ficheiro local preparado, **NOT RUN**. Não os contar como testes passados nem como 40.000 provas independentes do Windows.
- PC, contas, permissões, serviços e ficheiros pessoais não foram alterados por esta revisão.
- Verificação local da cópia publicada: 29 hashes do manifesto conformes; sintaxe dos 74 ficheiros Python Nexus válida. Estes dois controlos não executam o software nem demonstram segurança de SO.

## Revisão observada em 05-10-2026, 10:09 Lisboa

SHA analisado: `7faead619e14d15e5590f84e1d52ac68d1e58bc4`. A revisão documental posterior não constitui correção do runtime nem transfere PASS para o novo commit.

| Gate | Resultado nesse SHA |
|---|---|
| [Auditoria](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37274701729) | SUCCESS |
| [Integration Stress](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37274701734) | SUCCESS; regressão 1386 PASS |
| [Avatar Windows/Ubuntu](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37274701774) | 165 PASS em cada OS |
| [Nexus Windows](https://github.com/PAPACREATOR/cerebro-parvo-/actions/runs/37274701714) | **FAIL**: Core 140 PASS, Blocks 1068 PASS, All 1386 PASS, Practical **39 PASS / 1 FAIL** |

Falha: `test_real_windows_result_back_to_original_and_folha_after_restart[binary-attachment]`, em `test_reverse_flow.py`. A leitura de `runs/<id>/state.json` em `store.state()` devolveu `PermissionError`; o pedido HTTP terminou em `RemoteDisconnected`. `INTEGRITY=PASS`. Não é o controlo negativo de Python inexistente. Possível acesso concorrente/bloqueio de ficheiro é hipótese, não causa demonstrada.

Próximo gate: diagnosticar/reproduzir esta falha, corrigir minimamente quando a causa estiver identificada e repetir Practical, regressão e E2E. Um rerun verde isolado não prova resolução da causa. **Este SHA não tem PASS global.** As suites sobrepõem-se; não somar contagens.

## Última baseline funcional validada antes da limpeza documental

A baseline funcional `7e1ec9b6ce1804123c1cb4bd198ea2dfff5bd98a` passou duas execuções independentes dos gates principais:

- Kernel stress: 100.000 casos PASS;
- linguagem/ambiguidade: 100.000 casos PASS;
- MCP stdio: 1.000 operações PASS;
- OpenNotebook Kernel E2E: PASS;
- ACE-Step/Forge MCP health: 17 PASS;
- regressão completa: 1386 PASS;
- Core Windows: 140 PASS;
- Blocks: 1068 PASS;
- Practical: 40 PASS;
- avatar OpenNotebook: 165 PASS Windows + 165 PASS Ubuntu;
- auditoria histórica: 34 PASS;
- persistência ativa: 11 PASS.

A limpeza posterior é documental/organizacional. O HEAD resultante só passa a nova baseline depois de repetir os mesmos workflows e regressões.

## PC físico

O repositório já contém `nexus/windows/sync-nexus-pc.ps1` para atualizar uma única árvore Git local, validar o Nexus, instalar ACE-Step/Forge externamente e executar health checks.

O gate físico só fica fechado quando existirem, no PC:

- `C:\Nexus-Tools\pc-bootstrap.json`;
- `C:\Nexus-Tools\media-health.json`.

Sem esses relatórios, CI/GitHub PASS não é apresentado como PASS do hardware local.

## Pendências técnicas ainda reais

1. Fechar o confinamento Windows real acima antes de recomendar instalação/execução no PC; diagnosticar também o PermissionError histórico, mesmo com o Practical atual verde.
2. Fechar o E2E físico OpenNotebook 1.15 + SurrealDB + modelo local + Kernel + Creative + Human Gate + Canonical.
3. Escolher e validar um checkpoint Forge com licença conhecida antes de geração real.
4. Continuar os contratos ainda abertos em #3 (IMP-001) e #4 (G10/IMP-019 + eliminação controlada).
5. Integrar outras ferramentas externas apenas pelo mesmo processo: contrato → FAIL real → correção mínima → regressão → teste prático → E2E.

## Percurso do desenvolvimento

A [genealogia de decisões](../../DECISIONS.md) explica por fase o problema, a alteração, a razão e a evidência: receção/persistência, ferramentas existentes, Folha/bancada, testes Windows, simplificação Python/MCP e multimédia. Datas e resultados históricos não são apresentados como validação do HEAD atual.

## Documentação que permanece por função

### Contratos e fundamentos
- `F001.md` … `F013-PROVENIENCIA-INVERSA.md`
- `FUNDACAO-REVISTA-2026-10-01.md`
- `SCHEMAS-E-WINDOWS.md`
- `CONTRATO-RELATORIOS-MICROPROCESSO.md`
- `REGRA-PYTHON-MINIMO-FRONTDOOR-2026-10-04.md`

### Relatórios/evidência
- `RELATORIO-STRESS-100K-2026-10-04.md`
- `RELATORIO-APRENDIZAGEM-RECOVERY-2026-10-04.md`
- `RELATORIO-LAB-TESTES-POR-FASES-2026-10-04.md`
- `RELATORIO-AVATAR-2026-10-04.md`
- `AVATAR-CI-2026-10-04.json`
- `AVATAR-SYNC-CI-2026-10-04.json`
- `RELATORIO-FINAL-WIKI-100K.md`

### Comparações históricas preservadas
- `RELATORIO-KERNEL-SPIFF-CONDUCTOR-FASE1-2026-10-04.md`
- `RELATORIO-PERFORMANCE-CONDUCTOR-2026-10-04.md`

Estes dois últimos são evidência histórica e não descrevem o runtime ativo.

## Regra de continuidade

Uma alteração só passa a baseline se:
1. o bloco afetado passar;
2. qualquer FAIL for preservado e diagnosticado;
3. a correção mínima passar;
4. regressão completa passar;
5. testes práticos aplicáveis passarem;
6. E2E aplicável passar;
7. a PR #23 for atualizada com o resultado.

Não criar novas cópias de estado/continuidade para cada sessão. Atualizar este documento e a PR #23.

## Organização documental — pedido humano de 05-10-2026

Pedido: resumir, limpar e organizar o repositório. Revisão limitada a README principal, README Nexus, AGENTS, DECISIONS e este documento; sem apagar contratos, relatórios, comparações ou histórico. Corrigidas referências a executor retirado e documento removido; indicação explícita de candidato versus main, princípio versus composição histórica e PASS versus FAIL. PR #23 acompanha a entrega. Não foram alterados runtime, testes, licenças ou regras de autoridade.
