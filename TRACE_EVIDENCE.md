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
