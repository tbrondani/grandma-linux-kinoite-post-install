# Tamanho da instalação

Medição na VM em 16/11/2026:

- Apps Flatpak e runtimes do usuário: **7,36 GB** em disco.
- Tradutor Argos, Python e dez modelos: **2,67 GB** em disco. Os modelos exigem cerca de **880 MB** de download; as dependências são adicionais.
- Mapas de Portugal: **451 MB** de download e de arquivos instalados.
- Fastfetch e yyjson, adicionados após o inventário: **845 kB** de download informado pelo rpm-ostree e **2,41 MB** de arquivos instalados.
- Ajuda e ferramentas de backup: **0,066 MB** em disco. A primeira cópia da VM ocupou **1,16 MB** para 13 arquivos pequenos. O tamanho real depende dos arquivos pessoais e das versões guardadas; não está no total anterior.
- Dez dicionários: **13,5 MB** de download e **45,6 MB** de arquivos instalados.

Os mapas e dicionários já fazem parte das pastas de dados dos aplicativos. Não some esses valores duas vezes.

As pastas medidas ocupam **15,79 GB**, incluindo **4,94 GB de Flatpaks do sistema que já vieram com o Fedora**. Isso é um inventário atual, não o custo adicional exato do projeto. Ainda falta medir antes e depois em uma base limpa. Os tamanhos de download de Flatpaks são estimativas; não representam tráfego de rede medido.

Veja o [inventário por item](measurements/2026-11-16.md) e os [comandos de medição](INSTALLATION-SIZE.md).
