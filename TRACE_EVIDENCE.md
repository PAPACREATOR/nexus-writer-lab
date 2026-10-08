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
