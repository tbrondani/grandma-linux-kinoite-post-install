# Perfis de instalação

Sem arquivo, uma instalação nova usa a seleção completa atual e o idioma da sessão, em inglês ou PT-BR. Se já houver preferências salvas, elas serão reutilizadas. IA fica desativada até a integração existir.

Abra **Instalador** na área de trabalho. Escolha instalar/reparar, reconfigurar ou atualizar. Você pode usar o perfil salvo, indicar outro YAML ou gerar `grandma-profile.yaml` na pasta atual. Ao gerar o modelo, a instalação para: edite o arquivo antes de executar novamente.

```sh
~/.local/bin/grandma-install --template grandma-profile.yaml
~/.local/bin/grandma-install --config grandma-profile.yaml --dry-run
~/.local/bin/grandma-install --config grandma-profile.yaml --yes
```

Antes da primeira instalação, use `bash setup.sh` no lugar de `~/.local/bin/grandma-install`, ou passe as opções depois de `bash -s --` no comando curl do README.

Exemplo de perfil parcial:

```yaml
schema_version: 1
language: pt-BR
features:
  games: false
  translator: false
  remote_support: false
  ai: false
```

O que não estiver definido mantém a preferência salva ou o padrão inicial. Guarde seus perfis pessoais fora do repositório Git. Veja todas as opções no [modelo completo](../data/profile.example.yaml). Use dois espaços para indentar e `true`/`false` para as opções. O formato aceita mapas e valores simples; listas, aliases, tags e valores de várias linhas não são suportados.

`false` não desinstala programas nem apaga dados. Desabilitar backup para somente o agendamento do projeto; as cópias e a chave de recuperação continuam guardadas. Reconfigurar ou atualizar preserva papel de parede, tema e preferência de leitura. Mudanças de idioma e ambiente valem nas próximas sessões de login.

Use `grandma-install --list-apps` para listar os IDs dos programas. O mapa `applications` permite opções por programa; Brave e Dolphin continuam obrigatórios. Para mapas, dicionário ou suporte remoto, use a opção do componente em `features`.

O mapa `environment` aceita variáveis não secretas. Para remover uma variável em um perfil parcial, use `null`; `environment: {}` limpa as variáveis adicionais do projeto. Caminhos de execução, identidade, controles do interpretador e nomes de variáveis secretas não são aceitos. Configure o idioma em `language`.

## Reinstalação e histórico

As preferências ficam em `~/.config/grandma-linux/profile.yaml`. Guarde esse arquivo ou mantenha-o no home preservado. O estado observado fica em `~/.local/state/grandma-linux/installation.json`, separado das preferências. Ele informa usuário, home, montagem e disponibilidade dos programas; não é backup dos arquivos.

```sh
~/.local/bin/grandma-install --list-snapshots
~/.local/bin/grandma-install --from-snapshot ID_DO_SNAPSHOT --dry-run
~/.local/bin/grandma-install --from-snapshot ID_DO_SNAPSHOT --yes
```

O histórico privado registra o perfil e o resultado de cada execução. Reutilizar um snapshot seleciona suas preferências; não desfaz arquivos nem remove programas novos. O perfil é salvo antes de um reinício necessário. Atualizações respeitam essas escolhas, e novos componentes opcionais ficam desligados em perfis antigos até serem selecionados.

`system.username` e `system.home` conferem o usuário e o home existentes. `storage.mount_points` exige caminhos já montados. O pós-instalador não cria contas, move arquivos, altera fstab ou particiona discos. Prepare o home separado durante a instalação do Fedora e mantenha uma cópia fora do computador.

`vm.username` e `vm.autologin` valem somente para criar uma nova VM de testes. Eles não alteram uma VM existente nem o login do PC real. Ainda suportamos apenas Fedora Kinoite, Plasma 6, Wayland e x86_64.
