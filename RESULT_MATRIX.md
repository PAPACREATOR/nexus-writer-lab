# Matriz de resultados

Fonte exata: b4d50ab8469cf60dfa3228c7c34ef9a1285ac827.
Writer 26.2.6.2 arquivado; prazo Writer 45 s; fronteira original.
Execução sequencial: https://github.com/PAPACREATOR/nexus-writer-lab/actions/runs/37814878330

| Variante | Alteração efetiva | book | convert_pdf | Interpretação |
|---|---|---|---|---|
| A | Adapter original, sem alterações | FAIL/timeout | FAIL/timeout | Gate original confirmado; revisão dos artefactos pendente |
| B | UserInstallation dedicado já existe em A | RUNNING | RUNNING | Repetição idêntica, sem prova diferencial |
| C | Diretório pré-criado já existe em A | PENDING | PENDING | Repetição idêntica, sem prova diferencial |
| D | SID da tarefa recebe MODIFY herdado em A | PENDING | PENDING | Repetição idêntica; nenhuma concessão geral ou Full Control nova |
| E | --norestore já existe em A | PENDING | PENDING | Repetição idêntica, sem prova diferencial |
| F | A + apenas --nolockcheck | PENDING | PENDING | Uma flag nova |
| G | F + apenas --nologo | PENDING | PENDING | Uma flag nova |
| H | Combinação mínima justificada | NOT RUN | NOT RUN | Depende de uma melhoria reproduzível em A–G |

Não foi removida a configuração MacroSecurityLevel=3 para fabricar uma matriz
aparentemente independente. B–E são nomeados como repetições porque a hipótese
recebida propunha opções que já estavam no candidato. Resultados iguais não
provam causalidade. F e G são experimentos reais de uma variável por etapa.

O gate final do workflow permanece FAIL se qualquer caso falhar; os passos
continue-on-error servem para completar a recolha, não para converter FAIL em PASS.
Um PASS intermitente é FAIL e exige a regressão completa solicitada.
