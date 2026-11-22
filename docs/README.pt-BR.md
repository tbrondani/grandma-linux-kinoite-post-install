# Grandma Linux

[English](../README.md)

Projeto de configuração pós-instalação para Fedora Kinoite e KDE Plasma. O objetivo é facilitar as tarefas do dia a dia, com uma área de trabalho familiar e nomes claros para os aplicativos.

**Estado:** início do desenvolvimento. O script inicial foi testado em uma VM Fedora Kinoite 45. Os testes em hardware real e de aceitação da release ainda estão pendentes.

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

Sem `GRANDMA_REF`, o instalador usa a última release estável publicada. Se não houver release, ele para. Para fixar uma versão, passe `GRANDMA_REF=vX.Y.Z` ao Bash; uma tag inexistente gera erro. Use `GRANDMA_REF=main` apenas para desenvolvimento. A URL acima carrega o bootstrap da main, mas o código instalado vem da release selecionada.

Após a configuração, abra **Ajuda** ou **Manual de uso** na área de trabalho. Veja [backup local e recuperação](BACKUP.pt-BR.md).

## Atualizações

Abra **Atualizações** na área de trabalho ou em **Sistema**. Escolha **Configuração e manual Grandma Linux** para atualizar o projeto, ou **Sistema e aplicativos** para abrir o Discover. Veja [como atualizar](UPDATES.pt-BR.md).

## Perfis de instalação

Abra **Instalador** para reutilizar as preferências ou escolher um YAML. Use `./setup.sh --config perfil.yaml --dry-run` para conferir sem alterar nada. Veja [perfis e reinstalação](PROFILES.pt-BR.md).

Use a mesma URL com `bash -s -- --check` para consultar atualizações de uma instalação existente, sem aplicar mudanças. Use `bash -s -- --mode=update` para consultar e aplicar uma atualização publicada do projeto. Esses comandos usam o perfil salvo. Sem idioma informado, a primeira instalação usa inglês; as atualizações mantêm o idioma salvo.
