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
Resultados do ETW ainda em recolha; não foi declarada prova causal.
