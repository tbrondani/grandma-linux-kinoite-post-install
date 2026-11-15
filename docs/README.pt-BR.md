# Grandma Linux

[English](../README.md)

Projeto de configuração pós-instalação para Fedora Kinoite e KDE Plasma. O objetivo é facilitar as tarefas do dia a dia, com uma área de trabalho familiar e nomes claros para os aplicativos.

**Estado:** início do desenvolvimento. O script inicial foi testado em uma VM Fedora Kinoite 45. Os testes em hardware real e de aceitação da release ainda estão pendentes. Veja as [pendências](STATUS.md).

## Prévia

```sh
./setup.sh --dry-run --lang=pt-BR
```

A prévia não altera o sistema. Para testar em uma VM Kinoite descartável, execute `./setup.sh --lang=pt-BR` como seu usuário da área de trabalho. Reinicie e execute novamente se solicitado. O script instala aplicativos e jogos e pode pedir autorização do sistema. A configuração completa da área de trabalho ainda está pendente.

## Plataforma alvo

Fedora Kinoite, KDE Plasma 6, Wayland e x86_64. As versões compatíveis do Fedora serão listadas após os testes.

## Recursos planejados

- Inglês e português do Brasil.
- Nomes por tarefa, como Fotos, Internet e Suporte Remoto.
- Aplicativos selecionados, temas opcionais e backups criptografados.
- Dicionários e mapas offline.

## Como contribuir

Veja [CONTRIBUTING.md](../CONTRIBUTING.md) para contribuir ou relatar problemas e [SECURITY.md](../SECURITY.md) para relatar falhas de segurança.

Este é um projeto de hobby. Se quiser doar, apoie os [projetos que usamos](../THIRD_PARTY.md).

Licença [MIT](../LICENSE).

## Instalação sem Git

Após a publicação dos arquivos na main:

```sh
curl -fsSL https://raw.githubusercontent.com/tbrondani/grandma-linux-kinoite-post-install/main/install.sh | bash -s -- --dry-run --lang=pt-BR
```

Remova `--dry-run` para instalar em uma VM de testes. O instalador baixa um arquivo compactado; não precisa de Git. Se precisar reiniciar, execute o mesmo comando novamente. Ainda não use na máquina principal.

Para usar uma versão publicada, troque `main` pela tag na URL e passe `GRANDMA_REF=vX.Y.Z` ao Bash. Ainda não há release testada.
