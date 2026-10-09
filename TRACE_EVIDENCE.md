# Evidência IPC

Classificação causal atual: **NOT PROVEN**.

Hipótese externa: Carlos De La Torre / @radelqui,
https://github.com/PAPACREATOR/cerebro-parvo-/issues/36#issuecomment-6064316804
Recebida como hipótese, não como instrução nem patch aprovado.

## Observações confirmadas

O probe nativo criou mutexes, recusou CreateNamedPipeW no namespace legacy com
WinError 5 e permitiu LOCAL. Confirmado no PC e no workflow original do laboratório.
Isso prova a diferença de permissões dos nomes testados, não que Writer esteve
parado precisamente nessa chamada.

book e convert_pdf excederam os 45 s com stdout/stderr Writer vazios, mesmo com
UserInstallation dedicado, diretórios criados e --norestore. O diretório já recebe
o MODIFY herdado do SID da tarefa. Direitos adicionais não são uma solução aceita.

## Fonte LibreOffice do mesmo tag

- [sal/osl/w32/pipe.cxx, tag 26.2.6.2](https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/sal/osl/w32/pipe.cxx):
  monta o prefixo legacy independentemente do identificador do perfil. A criação
  usa CreateNamedPipeW; a abertura passa por WaitNamedPipeW e CreateFileW.
- [officeipcthread.cxx, mesmo tag](https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/app/officeipcthread.cxx):
  o bootstrap tenta criar/abrir um pipe num loop, com esperas e tratamento de erro.
- [app.cxx, mesmo tag](https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/app/app.cxx):
  --nolockcheck participa na condição do aviso de lock; isso não demonstra que
  elimina o bootstrap IPC.
- [Documentação oficial de parâmetros](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html):
  o parâmetro UserInstallation documentado usa **-env:**, como o candidato.

A alegação de que UserInstallation por si só muda o namespace para LOCAL é
**REFUTED para este caminho de código do tag**. Pode mudar o identificador; o
prefixo hardcoded não muda. Isso não prova o caminho executado pelo binário nem
exclui outros bloqueios de startup.

## Rastreio

Procmon não está disponível entre os comandos locais verificados. No runner
descartável, a ferramenta lab/trace-writer.ps1 guarda o inventário de ferramentas;
usa ETW nativo a seguir, sem elevar Writer, alterar token, Job ou timeout.

O recorder usa Microsoft-Windows-Kernel-File e Kernel-Process, regista a configuração,
guarda ETL, XML, relatório de perda e eventos filtrados pelos PIDs observados.
O ficheiro circular é limitado a 128 MiB: pode perder eventos iniciais; ausência
de evento não prova ausência de chamada. Sem stack + resultado + cronologia ou
intervenção causal validada, manter NOT PROVEN.

Ver as instruções oficiais de [logman](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/logman-create-trace)
e [tracerpt](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tracerpt).
Resultados recolhidos e revistos; não foi declarada prova causal.

## Resultado ETW

Execução https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37815673872: ambas as rotas falharam no timeout. O perfil efetivamente contém ACE herdada do SID da tarefa com máscara MODIFY 0x1301bf. O perfil contém MacroSecurityLevel=3. O observador identificou soffice.com e soffice.bin em AppContainer e no Job original; também registou TokenElevation=true, limitação documentada no relatório.

O tracerpt processou 1 080 640 eventos, 6 341 com PIDs amostrados; zero matches de pipe no filtro. O resumo declara zero Events Lost, mas o buffer circular reteve apenas 109 segundos: isso não prova cobertura de toda a primeira rota. Há erros de ficheiro, mas sem stack/intervenção causal não identificam o bloqueio. Correlação exploratória por Irp também pode sofrer reutilização; nonzero-status-events.json não é prova causal. Classificação permanece NOT PROVEN.

ETL original 128 MiB e XML 1,365 GB ficam no artefacto writer-etw-evidence (id 11567506747); o ZIP descarregado tem hash em lab-evidence/download-manifest.json. Os eventos filtrados e relatórios estão persistidos no Git em lab-evidence/etw. O ZIP original também está versionado em lab-evidence/trace-raw.zip (cerca de 30 MB), preservando ETL e XML independentemente da expiração do artefacto.

A alternativa oficial é fundamentada em https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/lib/init.cxx e https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/include/LibreOfficeKit/LibreOfficeKitInit.h. Desativar RequestHandler pela API documentada não prova que esse era o bloqueio observado. Nenhuma interceção Win32 nem alteração de IPC foi aplicada ao Writer.

## Procmon original A, conta normal — revisão final

## Retoma: esperas das threads (novo ensaio)

lab/trace-waits.ps1 usa System.Diagnostics.ProcessThread e a API Microsoft WCT
somente no recorder externo, filtrando a instalação da conta descartável.
Não suspende threads, não injeta código, não ajusta privilégios e não muda Writer.
O helper é terminado após a execução; não interfere com o Job da tarefa.
Um erro de consulta é preservado, não resolvido ampliando o token.
WCT pode omitir esperas não suportadas e necessita acesso às threads; um único
node não prova que a thread corre. Resultado ainda NOT RUN na preparação.
Referências: https://learn.microsoft.com/en-us/windows/win32/api/wct/nf-wct-getthreadwaitchain
e https://learn.microsoft.com/en-us/windows/win32/api/wct/ns-wct-waitchain_node_info.

## Evidência Procmon da primeira fase

Run: https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37822420842
Commit executado: 635a836; artefacto 11570414451. Recorder Microsoft assinado,
externo ao sandbox; Writer elevated=false, AppContainer/capabilities/Job conforme
o launcher original. Flag LPAC solicitado; leitura direta indisponível (erro 87).
Os três testes originais: 2 FAIL (book, convert_pdf), 1 PASS (canary IPC).
Job após comunicação: zero processos ativos, nos dois casos.

3 947 519 eventos CSV, 30 767 dos PIDs 4420/6812/4580 e 7792/7868/7960.
Janela 18:14:26.1116055–18:18:12.5926513 UTC. A primeira execução Writer está
presente desde 18:16:14 e a segunda desde 18:17:17; ambas terminam ao limite.
Os 366 ACCESS DENIED incluem tentativas de acesso a diretórios ancestrais e
pedidos Write DAC/Write Owner nos temporários do perfil. Essas tentativas são
seguidas por fallback SUCCESS sem esses direitos. PRIVILEGE NOT HELD no perfil
também é seguido por abertura SUCCESS sem Access System Security. Não provam
um perfil sem MODIFY nem justificam um grante mais amplo.

Não há evento com pipe OSL/SINGLEOFFICE dos PIDs Writer. Procmon não garante que
toda falha anterior à emissão de um IRP apareça como CreatePipe. O canary legacy
WinError 5 e LOCAL permitido prova a diferença observada no canary, não o caminho
de espera do Writer. Pilhas exportadas sem símbolos identificam módulos/offsets;
não constituem um dump das threads paradas. Causa do timeout: **NOT PROVEN**.

Evidência permanente: lab-evidence/procmon/summary.json, writer-events.json,
writer-stacks.zip (XML focalizado integral dos seis PIDs), stack-filter.json,
metadata e resultados originais em standard-user/. O filtro e seus hashes estão
preservados para reprodução. O PML e os exports sistémicos completos permanecem
no artefacto GitHub do run, sujeitos à retenção Actions; não os confundir com os
eventos focalizados permanentes. O XML completo tinha 24 929 560 305 bytes e o PML
2 371 246 885 bytes. O relatório não depende da disponibilidade futura do artefacto.

## Retoma — resultado de esperas

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37833226764,
SHA bf8d569: testes originais 2 FAIL/45 s, 1 PASS canary; conta normal,
runtime e seal originais restaurados. Evidência em lab-evidence/thread-waits/.
344 amostras dos PIDs Writer 8056 e 2688, todas WCT com um node e sem ciclo.
WaitReason: UserRequest 172, EventPairLow 129, Unknown 42, Executive 1.
As labels do .NET e WCT são observações dinâmicas distintas, não uma pilha
nem prova de que se trate de named pipe. Causa permanece NOT PROVEN.
Novo ensaio justificado: snapshots mínimos das threads aos 10 e 25 s, ProcDump
Microsoft externo e análise CDB offline. Sem clones, sem iniciar Writer fora
da fronteira, sem novo token para Writer nem alteração do limite de 45 s.
A recolha pode interromper brevemente o processo e afeta timing; é diagnóstico,
nunca prova de desempenho/solução. Ferramentas instaladas só no runner descartável.
Fontes: https://learn.microsoft.com/en-us/sysinternals/downloads/procdump e
https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/opening-a-crash-dump-file-using-cdb.

### Revisão do payload do próximo ensaio

O dispatch com ProcDump/dumps foi rejeitado pela revisão automática: dumps podem
conter dados sensíveis e esse payload/destino não estava explicitamente autorizado.
**NOT RUN**; nenhum dump foi capturado ou carregado. A preparação foi removida
do estado ativo, preservada apenas na história do commit 9b35a91.

Alternativa de menor exposição: CDB -pvr, não invasivo e sem suspensão, apenas
comandos `~* k`, `lm`, `q`. Sem .dump, display de memória, argumentos de funções,
clones, breakpoints ou injeção; artefacto limitado explicitamente a texto e JSON.
O caminho de símbolos aponta só para uma pasta local vazia. Os frames podem ser incompletos
ou desatualizados numa leitura sem suspensão; preservar essa limitação.
Referência: https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/cdb-command-line-options.

### Primeiro resultado do leitor de pilhas

Run 37835201974, SHA a385058: rotas originais 2 FAIL/45 s e canary PASS.
Oito invocações do CDB produziram só o cabeçalho, sem frames: **FAIL de recolha**,
não evidência de IPC. O ExitCode estava null: corrigido mantendo o handle do
processo antes de esperar e refrescando o estado. Teste local sintético de exit 7
confirmou o registo correto, sem executar Writer. Artefacto completo textual
preservado em lab-evidence/stack-text-first-raw.zip e ficheiros extraídos.
Antes de repetir, o workflow passa a verificar o leitor num helper PowerShell
sintético adormecido (não Writer), com saída/erro/code explícitos. O comando
CDB foi simplificado; isso é reparação do diagnóstico, não uma variante do produto.

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

## Retoma 09-10 — discriminar o diálogo de bootstrap

Ajuda de #36 relida; não há nova solução técnica publicada no laboratório.
A fonte do tag 26.2.6.2 coloca HandleBootstrapErrors antes de RegisterServices
ativar EnableHeadlessMode(false), que autocancela diálogos. Um diálogo de
bootstrap pode preceder esse mecanismo. dp_misc::generateOfficePipeId pode
rejeitar UserInstallation antes de qualquer API de pipe. Hipótese, NOT PROVEN.
Não inferir IPC a partir do canary nem aplicar grants gerais.

A raiz do symbol store redireciona pedidos que não correspondam a símbolos;
isso não prova indisponibilidade de ficheiro exato. bin/symstore.sh do mesmo tag
utiliza /compress; consultar nome CodeView + GUID/age e variante .pd_.
Leitura apenas de metadados em disco, sem dump. Fontes:
https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/bin/symstore.sh
https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/app/appinit.cxx
https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/app/app.cxx
https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/deployment/misc/dp_misc.cxx
https://mail-archive.com/libreoffice%40lists.freedesktop.org/msg368207.html

O observador LPAC adicional usa o AccessCheck sintético de Chromium
(CheckLpacToken). Duplica token só para consulta, sem impersonar/assignar ou
conceder direitos a objetos do sistema; World3/AAP1/ARAP2 discriminam LPAC=2
de AC normal=3. APIs falhadas continuam UNKNOWN. A consulta classe46 original
e o seu erro87 ficam preservados. Controlos ordinary/invalid handle não lançam Writer.
https://chromium.googlesource.com/chromium/src/+/refs/tags/133.0.6909.0/sandbox/win/src/app_container_test.cc

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

## Próximo diagnóstico: correspondência Microsoft e resolução offline

O primeiro leitor comparou apenas a idade PDBI com o PE. O código Microsoft
OpenValidate4 exige GUID exato, idade PDBI maior ou igual à do PE e idade DBI
igual à do PE. O leitor passa a verificar os três valores, preservando a idade
PDBI real e recusando a exceção legada DBI=0. Onze controlos sintéticos PASS,
incluindo GUID/DBI errados, INFO anterior, DBI ausente/zero e truncamento.
O age DBI do PDB oficial ainda não foi observado: o FAIL anterior mantém-se.
Fonte: https://github.com/microsoft/microsoft-pdb/blob/master/PDB/dbi/pdb.cpp#L808-L889
DbgHelp documenta PdbAge como a idade DBI:
https://learn.microsoft.com/en-us/windows/win32/api/dbghelp/ns-dbghelp-imagehlp_module64

As pilhas vivas continuam com símbolos locais vazios e leitor limitado a 8 s.
A resolução exata decorre depois da conclusão do Writer/Job, limitada a 120 s,
usando apenas PE/PDB em disco e endereços do texto já recolhido. DbgHelp do SDK
assinado deve confirmar a correspondência sem LOAD_ANYTHING ou ignore-match.
Nenhum processo Writer adicional, attach, leitura de memória ou dump offline.
Essa etapa identifica funções/call sites; não valida a conversão nem prova a
causa por si só. Timeout original de 45 s e fronteira mantidos.

## Repetição e símbolos oficiais verificados — 09-10-2026

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37903488590,
SHA 85a3696: duas rotas FAIL aos 45 s e canary IPC PASS; 3 testes, 108,080 s
totais. O campo launch_seconds do observador é um instante time.monotonic(),
não a duração de preparação. O ensaio anterior teve testes de 52,971 e
51,700 s, não 602 s de preparação. Não alterar o timeout por essa leitura.

CoInitializeEx retornou S_FALSE (COM já inicializado), mas quatro leituras
AccessibleObjectFromWindow continuaram HRESULT 0x800401F0. A hipótese de
que bastava inicializar COM no leitor não foi confirmada; o erro original
não pode ser atribuído só ao leitor. Nenhum texto do diálogo obtido.

O PDB oficial foi verificado: GUID exato, PDBI age=3, DBI age=2, PE age=2,
DBI moderno AMD64, private_symbols_stripped=false. A correspondência nativa
Microsoft passou, sem forçar símbolos. O leitor offline, porém, falhou antes
de carregar DbgHelp: subprocesso Windows PowerShell não completou a
verificação de assinatura. A etapa de instalação em pwsh verificou Valid,
Microsoft Corporation, dbghelp.dll SHA-256
140adb286a11fbdfb63b6d8dff30039c50ff9c88b6909be9ce8292680d5be2af.
Isso é falha diagnóstica, não causa do Writer nem PASS de resolução.

Run paralelo https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37904071891,
SHA 6c54cb1: somente PE/PDB em disco e pilhas anteriores, nenhum Writer
executado. Mesmo PDB verificado, mesma falha da verificação auxiliar antes
da resolução. Provas completas em lab-evidence/com-offline/ e prior-offline/,
com ZIPs integrais preservados. Próximo passo: corrigir e repetir apenas a
leitura offline. Causa Writer NOT PROVEN; proposta vazia e regressão de
solução NOT RUN. Loop ativo, principal intacto.

## Espera localizada com PDB correspondente — 09-10-2026

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37934454652,
SHA cd0c574, somente leitura offline: SUCCESS. DbgHelp assinado confirmou
SymPdb, GUID exato, PdbAge DBI=2, PdbUnmatched=false, DbgUnmatched=false,
SizeOfImage=148271104; nenhum ignore-match/LOAD_ANYTHING. Dez RVAs resolvidos
em 6,250 s. Não houve novo Writer, attach, dump ou leitura de memória.
Provas integrais: lab-evidence/frames-resolved/ e frames-resolved-raw.zip.

Nas quatro capturas anteriores dos dois PIDs bin, os call sites de retorno
menos um byte situam-se dentro dos limites dos símbolos Tag5 e têm linhas
correspondentes do build: Desktop::Main app.cxx:1331 →
Desktop::HandleBootstrapErrors :855 → Desktop::HandleBootstrapPathErrors
:698 → SalInstanceDialog::run → Dialog::Execute. Os endereços/labels originais
ficam preservados, distintos da resolução offline. Observação não atómica.

O ramo do código exato mostra BE_PATHINFO_MISSING e checkBootstrapStatus
diferente de DATA_OK antes de RegisterServices ativar cancelamento headless.
A espera nesse aviso de arranque está demonstrada. O FailureCode concreto,
o caminho/configuração que o provoca e uma correção continuam NOT PROVEN.
Não se atribui a causa a um ACCESS DENIED isolado nem se fecha o aviso para
obter PASS. Fonte:
https://github.com/LibreOffice/core/blob/libreoffice-26.2.6.2/desktop/source/app/app.cxx

A falha auxiliar de assinatura foi reproduzida localmente: Windows PowerShell
herdava módulos incompatíveis de pwsh através de Python. Removido PSModulePath
somente no ambiente do filho e importados módulos integrados por caminho
absoluto. Ficheiro de sistema assinado Valid PASS, ficheiro inexistente recusado
com stderr preservado, ambiente pai intacto. A execução offline confirmou a
correção; isso não altera nem valida Writer. Fonte:
https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath#starting-windows-powershell-from-powershell-7

Regressão preparada reforçada: cada shard de stress exige exatamente os
50 IDs previstos (25 book + 25 convert_pdf), sem duplicados/skips/IDs de outro
módulo. Cinco controlos sintéticos PASS. As conversões reais dessa bateria,
a agregação 100+100 e os restantes gates da solução continuam NOT RUN.
Loop ativo; MINIMAL_PATCH_PROPOSAL.md vazio; Nexus principal intacto.


## 09-10-2026 — atribuição dos acessos à pasta base e teste de localização

Run offline [37936886424](https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37936886424),
source dd9364e72acc9d5bbb14b0fe2599a103b9e2d34e, SUCCESS. Sem executar Writer,
sem attach e sem memória de processos. Artefacto original `lab-evidence/parent-denial-symbols.zip`,
SHA-256 a362fae8451248d2851a427e953344000a71abb0e3dccb46db6b2c4fca6568fd.
PDB oficial com GUID/DBI age correspondentes resolveu os dez RVAs originais de
cada um dos dois eventos Procmon anteriores (PIDs 4580/7960); todos dentro de
símbolos Tag5 com extensão e linha do build. RVAs Procmon não foram ajustados
como endereços de retorno CDB. Prova preservada em `parent-denial-symbols/`,
entrada em `bootstrap-parent-denials.json`, fontes em `parent-denial-source-map.json`.

Ambos os ACCESS DENIED sobre `C:\Users\NexusWriterLab\NexusWriterLab`
passam por `utl::checkStatusAndNormalizeURL` (bootstrap.cxx:300),
`Bootstrap::Impl::initialize` (:679), `dp_misc::generateOfficePipeId` (:294),
`PipeIpcThread::enable` (:722), `RequestHandler::Enable` (:691) e `Desktop::Init` (:531).
O tag exato valida BRAND_BASE_DIR em :637–639 e depois bootstrap.ini em :641;
a inlining em :679 por si só não identifica qual argumento. O caminho recusado,
a consulta FindFirstFileW e os ficheiros program/*.ini lidos com sucesso tornam
a atribuição à consulta da pasta base LIKELY. O valor de retorno SAL, estado
bootstrap e FailureCode não foram lidos nesses processos. A propagação
E_ACCES → DATA_UNKNOWN → INVALID_BASE_INSTALL → FailureCode 9 continua uma
inferência condicional do código, não um valor runtime observado.

Primeiro diagnóstico SAL [37937173980](https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37937173980)
FAIL antes de carregar SAL: o helper estava em repo/lab, fora dos read_roots.
Child Python observado LPAC positivo independente, conta normal, mesmo Job e
capabilities; Job final zero. Nenhuma consulta SAL nem rede foi executada.
Artefacto `sal-paths-baseline.zip`, SHA-256
9128e6e3278d0f5fcddc5da6043806ee6e8cf7f4f63f76a985899189733267e7.
Corrigido em 4bc89e1: helper sintético copiado para o work já atribuído; pacote
Nexus carregado pelo caminho absoluto original. Sem acrescentar read roots.
Repetição corrigida e comparação SAL de localização em curso.

Experiência de localização [37937906490](https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37937906490),
source d837eca0bfaddf558aa45e3b66b23900ed90ad15, em curso: cópia idêntica da
instalação sob o runtime Python que já tem leitura recursiva autorizada.
Comparações separadas de SAL, baseline CLI A e variante LibreOfficeKit I.
Verificação da árvore completa por nomes relativos, diretórios, tamanhos e
SHA-256, sem reparse points; quatro controlos sintéticos PASS. Nenhum novo ACE,
read_dirs, root geral, alteração Host/sandbox, elevação ou aumento dos 45 s.
O primeiro job SAL desse run usa ainda o helper anterior; só os jobs reais A/I
avaliam a localização nesse commit. Medição SAL corrigida corre separadamente.
Ainda não há solução reproduzível nem regressão real 100+100.
