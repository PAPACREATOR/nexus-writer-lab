# Relatório do laboratório — 08-10-2026

## Estado

**Loop retomado em 09-10-2026 por instrução humana, até solução validada.**
Em preparação: símbolos correspondentes ao build instalado, leitura de diálogo
pelo HWND exato e LPAC independente. As provas anteriores permanecem abaixo.

Retoma diagnóstica concluída sem solução reproduzível (resultado B).
Causa efetiva: **NOT PROVEN**. As pilhas reais apontam para espera em
diálogo/message loop (**LIKELY**), mas o motivo do diálogo não foi identificado.
Último run 37840879467: **2 FAIL / 1 PASS IPC**, Writer 45 s, conta normal,
Jobs finais com zero processos. Não há patch; Nexus principal intacto.
Folha e regressão de solução permanecem **NOT RUN**.

## Proveniência

SOURCE_REPOSITORY=PAPACREATOR/cerebro-parvo-
SOURCE_SHA=b4d50ab8469cf60dfa3228c7c34ef9a1285ac827

Primeiro commit: 3f4e085a12b551ccf99a80f503e08aae03b1b833,
com o SHA original como único parent e apenas SOURCE_BASELINE.md acrescentado.
O único remote de push local é PAPACREATOR/nexus-writer-lab.

## Baselines observados

1. Windows local 11, build 26200, Python 3.12.10, LibreOffice 26.8.0.3:
   o teste nativo não elevado confirmou legacy pipe WinError 5 e LOCAL permitido.
   book e convert_pdf ficaram BLOCKED na preparação da DACL (erro 5) antes
   do arranque Writer. Não é reprodução do timeout Writer; não ampliar direitos.
   O primeiro ensaio dentro da sandbox do agente teve erro 87 no launcher e
   sockets locais recusadas; também não é evidência do IPC do Writer.
   Um diagnóstico de stack local identificou propagação/limpeza de ACL como
   responsável pela preparação demorada. Os processos de teste terminaram.
2. [Workflow original](https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37813977363),
   commit 3f4e085, Windows Server 2025 10.0.26100, Python 3.12.10:
   2 FAIL/5 PASS. book e convert_pdf bloquearam no timeout Writer de 45 s;
   stdout/stderr Writer vazios. Legacy WinError 5; LOCAL criado.
   O pacote Chocolatey 26.2.6 descarregou **26.2.6.3**: a configuração original
   foi reproduzida, mas este resultado não substitui a prova do build 26.2.6.2.
   Os testes de conversão fora de LPAC deste workflow histórico não contam como
   PASS da solução solicitada.
3. [Matriz arquivada](https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37814878330),
   commit aa14ad8: instalador oficial arquivado 26.2.6.2, SHA-256
   788ce7d4b56460357f57552cb8cd848e8f2254f28f6e51fa61e0c65a18096373.
   A–G concluíram: 14 FAIL, 7 PASS. Cada variante manteve o timeout em ambas
   as rotas; o canary IPC passou. A confirmou o timeout antes de permitir B–G.
   Evidência: lab-evidence/sequential-matrix, incluindo comandos e hashes.

## Método e limites

Testes originais mantidos, sem retirar assertions. O observador externo lê apenas
processos da árvore da tarefa, comandos, token, Job e ficheiros sintéticos antes
da limpeza. Amostragem de 100 ms não é inventário completo; eventos rápidos podem
escapar. ETW é recolhido separadamente; não transformar impacto do rastreio em
tempo de baseline.

O timeout de Writer é 45 s; o timeout do worker Host e a espera da fixture
continuam os originais. Não confundir duração total da rota com o timeout Writer.
LPAC, Job e permissões não foram relaxados. Não foi usado um novo Host/Kernel/Store.

100 book + 100 convert_pdf, Unicode, espaços, paths longos, inputs inválidos,
restart, crash/recovery, execução consecutiva, ausência de órfãos, hashes,
LPAC/Job/rede e timeout: **NOT RUN como validação de solução**, pois nenhuma
variante passou até ao estado registado. Se surgir PASS, estes gates tornam-se
obrigatórios antes de preencher MINIMAL_PATCH_PROPOSAL.md.

## Continuação independente desta conversa

Consultar RESULT_MATRIX.md, TRACE_EVIDENCE.md e os artefactos dos workflows.
Conferir o SHA real em metadata.json e a versão/binário, não apenas o nome do
pacote. Repetir apenas experiências justificadas, preservar o FAIL e nunca
publicar no repositório principal. O material de diagnóstico está em lab/.

## Alternativa oficial em diagnóstico

Após a matriz sem melhoria, a alternativa I usa a API C LibreOfficeKit oficial
do mesmo tag, cuja inicialização desativa RequestHandler IPC. Um probe direto
no runner original produziu PDF, mas tinha TokenElevation=true. As duas rotas
integradas falharam. Na conta normal, ambos os processos falharam aos 45 s;
probes baseline, SAL_LOG e caminho longo também falharam. Não há PASS do produto.
Mantém launcher original, raízes do runtime instalado, MacroSecurityLevel=3,
Job e 45 s. Não é uma combinação de flags de A–G. Ver RESULT_MATRIX.md.

O pedido adicional de abrir a Folha e fazer testes totais será cumprido após solução reproduzível: abrir uma instância do laboratório, usar o Human Gate original e validar os 200 ensaios e restantes gates. Não declarar conclusão enquanto Writer falhar.

## Limitação do runner

O observador no runner GitHub regista TokenElevation=true nos processos observados, além de AppContainer=true, capabilities conformes e Job original. Não foi introduzido runas nem alterado o token, mas esta herança do runner impede afirmar execução não elevada comprovada. Qualquer futura solução exige também validação numa sessão Windows não elevada. O ensaio local não elevado falhou antes de Writer na DACL; não substitui esse gate.

Foi criada uma conta normal exclusivamente nos runners descartáveis, com Python
e LibreOffice copiados pela própria conta para diretórios seus. Os testes
confirmaram elevated=false; não se adicionou a conta a Administrators e nenhum
grante geral foi aplicado. A instalação deslocada é uma diferença de ambiente,
documentada; não atribuir o contraste à elevação isoladamente.

Rotas reais não elevadas: https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37821690122.
Probes não elevados: https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37821697393.
Pós-comunicação das rotas: Job com zero processos ativos. Consulta direta de
TokenIsLessPrivilegedAppContainer devolveu WinError 87; não afirmar uma medição
direta desse flag. A opção LPAC original e o canary são mantidos.

O rastreio Procmon do adapter original, sem variante de conversão, está em
https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37822420842.
O recorder externo exige direitos de instalação próprios do runner; Writer
continua na conta normal e na fronteira original. Não se desativa política
Windows nem se muda o token de Writer. Revisão concluída: 3 947 519 eventos, dos quais 30 767 pertencem aos seis PIDs
do worker/Writer das duas rotas. Ambas falharam aos 45 s, IPC canary PASS.
A gravação cobre 18:14:26–18:18:12 UTC e inclui o arranque e a terminação.
Não foi observado um CreatePipe com nome OSL/SINGLEOFFICE dos PIDs Writer;
essa ausência não prova que a API não foi chamada ou identifica o motivo da espera.
Os erros de acesso ao perfil são seguidos por abertura/escrita bem-sucedidas.
Não ampliar direitos com base em erros recuperados. Ver TRACE_EVIDENCE.md.

As suites de 100+100, inputs adversos e regressão geral do candidato foram
preparadas em writer-lab-full.yml, mas **NOT RUN**: o gate das rotas reais falhou.
Os testes gerais verdes sobre os bytes originais não validam a variante I.

## Encerramento

Este é o encerramento da primeira fase, preservado; a investigação foi retomada.

A–G não melhoraram o resultado; H não tem combinação justificada. A alternativa
I falhou nas rotas reais e nos três probes não elevados. Procmon e ETW não
identificaram uma causa causalmente demonstrada. Alterar permissões, segurança,
Host ou o limite de 45 s excederia o pedido e não seria uma solução válida.
MINIMAL_PATCH_PROPOSAL.md continua vazio. Folha e testes totais de uma versão
corrigida ficam **NOT RUN**, porque o requisito prévio de correção não foi atingido.
Todos os resultados focalizados e procedimentos ficam persistidos neste repositório.

## Retoma — resultado de esperas

Run https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37833226764,
SHA bf8d569: testes originais 2 FAIL/45 s, 1 PASS canary; conta normal,
runtime e seal originais restaurados. Evidência em lab-evidence/thread-waits/.
344 amostras dos PIDs Writer 8056 e 2688, todas WCT com um node e sem ciclo.
WaitReason: UserRequest 172, EventPairLow 129, Unknown 42, Executive 1.
As labels do .NET e WCT são observações dinâmicas distintas, não uma pilha
nem prova de que se trate de named pipe. Causa permanece NOT PROVEN.
A proposta de ProcDump foi rejeitada por auto-review por possível exposição de dados sensíveis e NÃO EXECUTADA. O procedimento ativo usa CDB -pvr, texto de pilhas e módulos, sem suspensão ou dumps. As tentativas do leitor e os respetivos erros estão documentados em TRACE_EVIDENCE.md; só o self-check real com frames permite executar Writer.

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
