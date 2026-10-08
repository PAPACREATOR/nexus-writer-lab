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

Cada caso: 3 testes originais, 2 falhas (book e convert_pdf) e 1 PASS (canary IPC). Total da matriz: 14 FAIL, 7 PASS. Todos os casos restauraram os bytes originais e verificaram a integridade antes de executar. Evidência persistida em lab-evidence/sequential-matrix. H não tem melhoria em A–G que justifique uma combinação.
