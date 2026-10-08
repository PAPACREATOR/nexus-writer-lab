# Relatório do laboratório — 08-10-2026

## Estado

Investigação em execução. Nenhuma solução reproduzível nem proposta de patch.
O Nexus principal não foi alterado. Relatório provisório até ao fecho da matriz
e revisão do rastreio; não declarar A ou B do pedido concluídos antecipadamente.

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
   A concluiu com FAIL, e o gate confirmou a mensagem de timeout original antes
   de permitir B–G. Restantes resultados serão incorporados após conclusão.

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
