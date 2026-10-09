# Matriz de resultados

Fonte exata: b4d50ab8469cf60dfa3228c7c34ef9a1285ac827.
Writer 26.2.6.2 arquivado; prazo Writer 45 s; fronteira original.
Execução sequencial: https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37814878330

| Variante | Alteração efetiva | book | convert_pdf | Interpretação |
|---|---|---|---|---|
| A | Adapter original, sem alterações | FAIL/timeout | FAIL/timeout | 2 FAIL, 1 PASS; artefactos revistos |
| B | UserInstallation dedicado já existe em A | FAIL/timeout | FAIL/timeout | Repetição idêntica, sem prova diferencial |
| C | Diretório pré-criado já existe em A | FAIL/timeout | FAIL/timeout | Repetição idêntica, sem prova diferencial |
| D | SID da tarefa recebe MODIFY herdado em A | FAIL/timeout | FAIL/timeout | Repetição idêntica; nenhuma concessão geral ou Full Control nova |
| E | --norestore já existe em A | FAIL/timeout | FAIL/timeout | Repetição idêntica, sem prova diferencial |
| F | A + apenas --nolockcheck | FAIL/timeout | FAIL/timeout | Uma flag nova |
| G | F + apenas --nologo | FAIL/timeout | FAIL/timeout | Uma flag nova |
| H | Combinação mínima justificada | NOT RUN | NOT RUN | Depende de uma melhoria reproduzível em A–G |

Não foi removida a configuração MacroSecurityLevel=3 para fabricar uma matriz
aparentemente independente. B–E são nomeados como repetições porque a hipótese
recebida propunha opções que já estavam no candidato. Resultados iguais não
provam causalidade. F e G são experimentos reais de uma variável por etapa.

O gate final do workflow permanece FAIL se qualquer caso falhar; os passos
continue-on-error servem para completar a recolha, não para converter FAIL em PASS.
Um PASS intermitente é FAIL e exige a regressão completa solicitada.

## Alternativa I — LibreOfficeKit oficial

H continua reservado à combinação mínima de A–G, não executada porque nenhuma
dessas variantes melhorou o resultado. I é uma hipótese independente. Os primeiros
artefactos de I foram etiquetados H pelos scripts; são mantidos sem reescrever a
história e a etiqueta foi corrigida para futuras execuções.

| Ensaio de I | Resultado | Limite da conclusão |
|---|---|---|
| Probe direto 37817330801, runner original | Um PDF, exportação perto de 1 s | TokenElevation=true; não é solução válida nem PASS do produto |
| Rotas 37818090643 | 2 FAIL, 1 PASS canary | Erro de bootstrap do auxiliar; corrigido sem novos grants |
| Rotas 37818655960 e 37819386555 | 2 FAIL, 1 PASS por execução | Falha nativa durante inicialização; terceira execução regista 0xC0000409 |
| Rotas 37821690122, conta normal | 2 FAIL/45 s, 1 PASS canary | AppContainer e Job observados, elevated=false; zero processos ativos no Job após comunicação |
| Probes 37821697393, conta normal | Baseline, SAL_LOG e caminho longo: 3 FAIL/45 s | Rede recusada com 10013; nenhum PDF |

Execuções 37820186594, 37820479695, 37821029914 e 37821036415 falharam na
preparação da conta de teste: **NOT RUN**, sem converter essa falha em evidência
de Writer. Logs e correções estão versionados. A via I não constitui solução
reproduzível no estado observado. A causa do timeout original continua NOT PROVEN.

Cada caso: 3 testes originais, 2 falhas (book e convert_pdf) e 1 PASS (canary IPC). Total da matriz: 14 FAIL, 7 PASS. Todos os casos restauraram os bytes originais e verificaram a integridade antes de executar. Evidência persistida em lab-evidence/sequential-matrix. H não tem melhoria em A–G que justifique uma combinação.

Procmon A em conta normal, run 37822420842: **2 FAIL / 1 PASS**; timeout 45 s nas duas rotas, Job final zero. Causa final **NOT PROVEN**. Encerramento B, sem patch; Folha e regressão de solução **NOT RUN**.

## Retoma — resultado de esperas

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37833226764,
SHA bf8d569: testes originais 2 FAIL/45 s, 1 PASS canary; conta normal,
runtime e seal originais restaurados. Evidência em lab-evidence/thread-waits/.
344 amostras dos PIDs Writer 8056 e 2688, todas WCT com um node e sem ciclo.
WaitReason: UserRequest 172, EventPairLow 129, Unknown 42, Executive 1.
As labels do .NET e WCT são observações dinâmicas distintas, não uma pilha
nem prova de que se trate de named pipe. Causa permanece NOT PROVEN.
A proposta de ProcDump foi rejeitada pela revisão automática e NÃO EXECUTADA. Foi substituída por texto de pilhas não invasivo, sem dumps.

## Pilhas textuais — segunda tentativa

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37836600860, SHA 5bd8b1a. O leitor devolveu exit code 0 mas nenhuma pilha, também no helper sintético. Não é PASS do leitor nem evidência causal do Writer. Rotas originais: 2 FAIL, 1 PASS IPC. ZIP e textos preservados em lab-evidence/stack-text-second*.

Próxima verificação: opções antes do alvo -p, comandos iniciais -c em vez de -cf; self-check exige frames e interrompe o workflow antes de instalar/executar Writer se falhar. Modo -pvr sem suspensão mantido, sem dumps.

## Leitor — erro concreto isolado

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37838242509, SHA 3b84795: self-check FAIL, Writer NOT RUN. stdout contém `cdb: The system does not support detach on exit`. O erro não aparecia no ficheiro -logo: analisar stdout também é necessário. Removido apenas -pd, mantendo -pvr não invasivo e sem suspensão, texto de pilhas/módulos e nenhum dump. Self-check continua obrigatório. Em modo não invasivo o debugger não estabelece um debug attach ao alvo (Microsoft: https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/noninvasive-debugging--user-mode-). Não é uma alteração do Writer.

## Leitor — pilhas obtidas no helper

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37838559869, SHA 46f0677: exit 0, pilhas efetivamente presentes, Suspend: 0. Writer NOT RUN porque o validador procurava números de frame que o comando k não imprime. Corrigida a validação para cabeçalho Child-SP/RetAddr seguido de linha com dois endereços e Call Site; sem mudar os comandos ou ampliar payload. Evidência integral em stack-reader-fourth*. Isto valida a ferramenta no helper sintético, não resolve Writer.

## Pilhas reais obtidas — nova hipótese delimitada

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37838902004, SHA 6c7521b: self-check PASS com frames; oito capturas CDB textuais, exit 0, -pvr. Originais 2 FAIL/45 s, 1 PASS IPC; conta normal, runtime/restauro iguais ao source. Evidência integral em lab-evidence/stack-text-valid*.

soffice.bin PIDs 6760/6132 aos 10 e 25 s: thread principal `NtUserGetMessage -> GetMessageW -> vclplug_winlo -> Application::Execute+0x15b -> Dialog::Execute+0x8f`. O launcher soffice.com espera via NtUserMsgWaitForMultipleObjectsEx. Estado consistente nos quatro snapshots das duas rotas. Espera em diálogo/message loop: **LIKELY**; identidade/motivo do diálogo e causa efetiva: **NOT PROVEN**. Sem PDB correspondente, exports+offsets não identificam exatamente todas as funções. Não prova ausência de falha IPC anterior.

Próximo diagnóstico mínimo: EnumWindows/EnumChildWindows, GetWindowTextW/GetClassNameW/IsWindowVisible, apenas PIDs filtrados do Writer original no runner sintético. Sem WM_GETTEXT, mensagens, cliques, fechar janelas, UI Automation, suspensão, escrita de memória ou dumps. GetWindowTextW entre processos lê captions; não garante texto de controlos. Diagnóstico, não correção.
Fonte: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw.

## Janela confirmada, mensagem ainda não identificada

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37839902959, SHA 57d6914: duas rotas FAIL/45 s, canary PASS; Job final 0, AppContainer/Job/capabilities observados, elevated=false. Consulta LPAC classe 46 continua erro 87 (não inferir lpac=false). PIDs bin 1744/5188: SALFRAME visível, título LibreOffice 26.2 aos 10 e 25 s. Pilhas repetem espera em Dialog::Execute. Janela e espera PROVEN como observação; motivo/causa NOT PROVEN. GetWindowTextW não revelou mensagem/child controls. Runtime original intacto.

Última leitura delimitada: helper externo UI Automation lê apenas propriedades Name de Text/Button descendentes da janela SALFRAME LibreOffice 26.2 do PID Writer sintético filtrado. Sem padrões/actions, clicar, fechar, ativar, alterar accessibility settings ou conteúdo do documento. Helper limitado a 3 s, morto apenas ele se ultrapassar; Writer mantém 45 s. Esta consulta pode envolver provider accessibility e não é observação atómica; nunca prova de desempenho/solução. Não recolhe dumps.

## Resultado da retoma — 08-10-2026

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37840879467, SHA ebbab11: self-check do leitor PASS; testes originais **2 FAIL / 1 PASS IPC**, timeout Writer 45 s. Conta normal, AppContainer/capabilities/mesmo Job observados; zero processos ativos nos dois Jobs após conclusão. Runtime e selo originais verificados/restaurados. Consulta LPAC classe 46 continua sem suporte (erro 87): não é prova de ausência nem verificação independente positiva de LPAC.

Oito consultas de etiquetas retornaram listas vazias. Não permitem inferir que o diálogo não tem mensagem; não registam contagem de janelas/descendentes acessíveis. Limitação explícita do método. Pilhas reais e janela SALFRAME LibreOffice 26.2 foram persistidas: espera em diálogo/message loop **LIKELY**, causa exata **NOT PROVEN**. Nenhuma correção válida emergiu das hipóteses examinadas nesta retoma. Resultado B permanece: relatório/evidência completos para estes ensaios, sem declarar Nexus resolvido.

As provas integrais estão em lab-evidence/dialog-labels/ e dialog-labels-raw.zip, além das tentativas anteriores identificadas. As tentativas falhadas do leitor não são PASS do Writer. ProcDump foi rejeitado e nunca executado; a alternativa textual não carrega memória bruta. MINIMAL_PATCH_PROPOSAL.md permanece vazio. Folha e regressão de solução 100+100 permanecem **NOT RUN**, pois não existe solução comprovada. Principal intacto. Sem execução adicional pendente.

## Metadados e controlos — 09-10

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37900610141,
SHA 74e570c: controlos LPAC AccessCheck ordinary/invalid PASS, sem iniciar Writer.
mergedlo.pdb CodeView GUID 4b71bc20-183e-451a-b4b5-6aedb5de7413, age2,
key 4B71BC20183E451AB4B56AEDB5DE74132. Identificadores dos quatro binários e
hashes preservados em lab-evidence/debug-metadata/ e raw ZIP. Isso não valida
um símbolo ainda não obtido nem a conversão. A leitura real de LPAC/diálogo terminou no run 37900791913; resultado abaixo.

## Fronteira confirmada; leitor em correção — 09-10-2026

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37900791913,
SHA 31fa784: duas rotas FAIL aos 45 s e canary IPC PASS; Jobs finais com zero
processos. Todos os dez eventos observados de Python/conhost/soffice.com/
soffice.bin tiveram AccessCheck api_ok=true, AppContainer=true,
AccessStatus=true, granted_access=2, lpac=true; conta não elevada e mesmo
Job/capabilities. LPAC verificado independentemente. O erro 87 da consulta
classe 46 fica preservado; não é tratado como false. O inventário a cada
0,1 s não prova a ausência de processos com duração inferior ao intervalo.
Provas integrais: lab-evidence/exact-msaa/ e exact-msaa-raw.zip.

MSAA pelo HWND exato encontrou o SALFRAME correto, mas retornou HRESULT
0x800401F0 (CO_E_NOTINITIALIZED): falha do leitor, não ausência do provider.
CoInitializeEx foi acrescentado ao helper externo, sem mudar Writer.
S_OK/S_FALSE são balanceados; RPC_E_CHANGED_MODE preserva o apartamento
existente. Parser e compilação C# PASS; execução real da correção NOT RUN.
Fonte: https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coinitializeex

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37901277588,
SHA a19d2d6: preparação de símbolos FAIL; Writer NOT RUN. O CAB oficial foi
descarregado e expandido corretamente. SHA-256 do CAB:
e70b64c6844a809dd42f1b4ea9a06a843d3cc17d2ffd48742f391e4aa268dd17.
mergedlo.pdb tem GUID 4b71bc20-183e-451a-b4b5-6aedb5de7413 correspondente,
mas age=3 no stream PDBI, enquanto o PE exige age=2. O leitor recusou o
ficheiro; não se forçou correspondência nem se atribuiu uma causa ao Writer.
Provas: lab-evidence/symbol-age-mismatch/ e symbol-age-mismatch-raw.zip.

Regressão preparada: oito módulos nexus/security_tests incluídos, skips ou
módulos obrigatórios ausentes causam falha; adversos exigem Job/token e uma
sequência real de quatro pedidos no mesmo Host/store, com aprovação e
restart sem replay. Controlos de classificação PASS; 17 contratos de
segurança documentais PASS. Conversões desta regressão NOT RUN até existir
solução. O gate LPAC exige a leitura independente positiva; conflitos ou
evidência inconclusiva continuam a falhar. Não é PASS global.
