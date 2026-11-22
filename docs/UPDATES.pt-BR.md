# Atualizações

Abra **Atualizações** na área de trabalho ou em **Sistema**.

1. Escolha **Configuração e manual Grandma Linux**.
2. Confira as versões e confirme a atualização.
3. Mantenha o computador ligado até a janela de progresso fechar.
4. Se for solicitado, reinicie e escolha a mesma opção para concluir.

O pacote verificado fica salvo entre reinícios. Seu papel de parede, preferências de leitura, atalhos existentes e configurações de backup são preservados. Atalhos removidos da área de trabalho não voltam. Novos temas ficam disponíveis sem mudar a aparência selecionada. Se houver erro, escolha **Ver o registro da última atualização do projeto** e tente novamente.

Para atualizar Fedora e os aplicativos Flatpak, escolha **Sistema e aplicativos**. O Discover faz essas atualizações. Modelos de tradução, catálogos de mapas e configurações do projeto acompanham as versões do Grandma Linux.

Pelo terminal, sem Git e sem sudo:

```sh
~/.local/bin/grandma-update --check
~/.local/bin/grandma-update --apply --lang=pt-BR
```

O segundo comando pede confirmação. Se precisar reiniciar, execute-o novamente depois. Código 75 indica reinício necessário; 1 indica erro. A instalação de novos pacotes do sistema pode pedir autorização. O atualizador não reinicia o computador sozinho.

Enquanto não houver uma release estável publicada com o pacote de atualização, a ferramenta informará que não há versão disponível. Ela não instala branches de desenvolvimento.

Se uma atualização salva falhar repetidamente, escolha **Recomeçar a atualização do projeto**. Confirme para descartar o pacote salvo e busque a versão mais recente novamente. Os aplicativos instalados e suas configurações são mantidos.
