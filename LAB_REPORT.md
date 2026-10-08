# Relatório do laboratório — 08-10-2026

## Estado

Resultado B: hipóteses razoáveis desta investigação esgotadas sem solução
reproduzível. Causa efetiva: **NOT PROVEN**. Não há proposta de patch.
O Nexus principal não foi alterado. O laboratório fica concluído como diagnóstico,
e não como resolução do Nexus.

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

A–G não melhoraram o resultado; H não tem combinação justificada. A alternativa
I falhou nas rotas reais e nos três probes não elevados. Procmon e ETW não
identificaram uma causa causalmente demonstrada. Alterar permissões, segurança,
Host ou o limite de 45 s excederia o pedido e não seria uma solução válida.
MINIMAL_PATCH_PROPOSAL.md continua vazio. Folha e testes totais de uma versão
corrigida ficam **NOT RUN**, porque o requisito prévio de correção não foi atingido.
Todos os resultados focalizados e procedimentos ficam persistidos neste repositório.
