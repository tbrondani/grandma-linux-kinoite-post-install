# Backup local

A configuração faz a primeira cópia e agenda uma cópia mensal de Área de trabalho, Documentos, Downloads e Imagens. Mantém 12 versões mensais e 3 anuais, além da última cópia. O computador precisa estar ligado e com sua sessão aberta. Uma execução perdida é tentada quando a sessão voltar a iniciar.

- **Utilitários → Backup:** fazer uma cópia agora, conferir a última cópia ou abrir a pasta do backup.
- **Utilitários → Recuperar arquivos:** escolher uma versão e onde recuperá-la. Os arquivos ficam em uma pasta nova; os arquivos atuais são preservados.
- Para usar uma cópia de outra instalação, escolha **Abrir uma pasta de backup guardada**. Isso não muda o backup automático atual.

A pasta padrão é `~/.local/share/grandma-linux/backups/local`. Para levar a cópia para outro lugar, copie essa pasta inteira, incluindo `repository`, `grandma-backup.json`, `recovery-key.txt` e `RECOVERY.txt`. O repositório é criptografado. A chave acompanha o conjunto para permitir a recuperação local; quem tiver ambos poderá ler a cópia. Mantenha a pasta privada.

Ao reinstalar, preserve essa pasta ou copie-a para outro lugar antes. Formatar o disco também apaga o backup que está nele. A cópia contém arquivos pessoais, não uma imagem do sistema. Após reinstalar, execute a configuração Grandma Linux, abra Recuperar arquivos e selecione a pasta guardada.

Quando existir, o arquivo `~/.config/grandma-linux/profile.yaml` também entra na cópia. A recuperação coloca o perfil em `.config/grandma-linux/profile.yaml` dentro da pasta nova de recuperação. Escolha esse arquivo no Instalador para reutilizar as preferências; o perfil em uso não é sobrescrito.
