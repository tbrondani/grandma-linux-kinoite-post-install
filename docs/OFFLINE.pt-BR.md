# Mapas e dicionários offline

A configuração baixa os mapas de Portugal automaticamente. O script usa o catálogo do Organic Maps instalado e confere o tamanho e o hash de integridade (SHA-1 ou BLAKE3) de cada arquivo. Reabra Mapas após a instalação. Abra Portugal e desconecte a internet para conferir o mapa.

Para outra região, execute `python3 scripts/maps.py --region Brazil_Bahia` na pasta do projeto. Use o identificador exato da região no catálogo do aplicativo. O Brasil não é baixado por padrão.

A configuração também instala dicionários de português para inglês, espanhol, francês, alemão e italiano, nos dois sentidos. Abra Dicionário e selecione um deles. Eles traduzem palavras, não textos completos.
