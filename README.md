# Tradutor de Aulas

## Executar no Windows

Execute `iniciar.bat` e use o endereço `http://127.0.0.1:5001` aberto no
navegador. Não abra `index.html` diretamente: a tradução precisa do aplicativo
Flask e do serviço LibreTranslate.

Mantenha abertas as janelas do Tradutor de Aulas e do LibreTranslate enquanto
estiver usando o site. O inicializador verifica se ambos os serviços iniciaram
antes de abrir a página.

Na primeira inicialização, o LibreTranslate precisa de internet para baixar os
modelos de português, inglês e espanhol. Depois, as traduções usam os modelos
locais. O aplicativo aceita arquivos PDF, DOCX e PPTX de até 10 MB e baixa os
resultados como TXT. PDFs compostos apenas por imagens precisam de OCR, que não
está incluído.

O inicializador usa `.venv\Scripts\python.exe` quando suas dependências estão
instaladas; caso contrário, procura um Python funcional no `PATH`. Instale as
dependências do aplicativo com `python -m pip install -r requirements.txt` se
necessário. O LibreTranslate deve estar em `.venv-lt\Scripts\libretranslate.exe`
ou disponível no `PATH`.

As pastas dos ambientes virtuais e caches estão no `.gitignore`; elas continuam
no computador, mas não devem ser incluídas nos commits.

## Testes

Execute `python -m unittest -v test_app` para validar a extração dos formatos,
o envio à API e o tratamento de erros.
