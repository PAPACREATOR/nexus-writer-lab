# Writer: Sandy v0.9994, pipe LOCAL — ensaio isolado

Pedido humano de 10-10-2026: usar na bancada a solução pública enviada pelo
autor. Base congelada: `e22b33190e6144e800f69a05677f458e818d6e75`.
Branch exclusiva: `lab/writer-mail-pipe-rename-20261010`.

Este ensaio reutiliza as funções e o TOML do launcher MIT de Hrvoje Abraham:
https://github.com/ahrvoje/sandy_cli/tree/aefeeee631518cd2d7197300a6e1a67f0c63eb63
Release v0.9994: SHA256
`cbfc30709f80e63b201f1944c34692fc430d8aa42d6cd2823fcc670675307eac`.
Conservar a licença upstream no artefacto. Não copiar emails privados.

## Experiência

Windows descartável, conta padrão comprovada, Writer oficial 26.2.6.2.
Inicializar fora LPAC apenas com documento sintético; guardar snapshot do perfil
antes de qualquer alteração posterior. Reutilizar o ODT sintético já existente
em `test_native_writer_route_real.document`, gerado uma única vez.
Restaurar a snapshot para o mesmo caminho antes de cada variante.
A e B usam a mesma instalação, perfil, input, ambiente, comandos e ACLs.
A única diferença no TOML é a presença de `[pipes]` em B.
Lançar `soffice.bin` diretamente em Sandy LPAC, filhos/rede desativados.
Máximo 45 s por conversão: 43 s de execução + até 2 s de terminação/verificação.
Recuperação posterior das ACLs é registada separadamente, nunca aumenta o prazo.

## Evidência e critérios

Guardar comandos, durações, stdout/stderr, TOMLs, logs Sandy, hashes e resultados
mesmo em falha. B deve terminar com exit 0 e PDF validado pela função existente
`office.pdf_bytes`. A extração textual independente deve conter o texto do ODT.
Comprovar token real Writer não elevado, AppContainer, LPAC por dois métodos,
Low integrity, capabilities exatas `registryRead` + `lpacCom` e pipe exato.
Testar acessos reais por impersonação do token: input/output permitidos,
runtime e controlos sem escrita, canário externo sem leitura/escrita,
documento sem permissão de execução. Verificar hashes originais, DACLs,
remoção do hook, desregisto Sandy e ausência de Writer sobrevivente.

PASS laboratorial abrange apenas esta conversão e estes acessos quando todos
forem observados. Se A também exportar, atribuição causal ao pipe é INCONCLUSIVE.
Falha de conversão é FAIL; prova ausente é NOT RUN/INCONCLUSIVE, nunca PASS.
Rede, clipboard e criação de filhos têm flags/capabilities inspecionadas; testes
comportamentais próprios permanecem NOT RUN neste ensaio. Host, Human Gate,
rotas `book`/`convert_pdf`, regressão 100+100 e PC pessoal também NOT RUN.
Não modificar Kernel/Host/Store, outros workflows ou branches. Sem merge.

Backup antes das adições: bundle completo e restauro bare verificados no scratch;
SHA256 `e7aaeefc6982bfe894946b035fe7daccb955b8f8a68637983f103e279175a065`.
Nenhum ficheiro existente foi alterado para este ensaio.
