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
um símbolo ainda não obtido nem a conversão. A leitura real de LPAC/diálogo
em curso no run37900791913, SHA31fa784; resultado ainda NOT RUN/PENDING.
