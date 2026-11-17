# Tradutor de Aulas

Aplicação local Flask para extrair texto de arquivos PDF, traduzir para
português, inglês ou espanhol e visualizar/baixar o resultado em TXT, DOCX,
PPTX ou PDF.

O envio para tradução aceita somente arquivos PDF. Os formatos de download
continuam sendo TXT, DOCX, PPTX e PDF.

## Instalação e execução no Windows

1. Instale Python 3.13.2 para Windows e confirme que o Python Launcher está
   disponível. No PowerShell, verifique:

   ```powershell
   py -3.13 --version
   ```

2. Abra o PowerShell na pasta do projeto e execute:

   ```powershell
   .\iniciar.bat
   ```

   Na primeira execução, o inicializador cria `.venv` com Python 3.13. Se as
   dependências ainda não estiverem instaladas, ele pergunta antes de instalá-las
   nesse ambiente virtual. Não é necessário adicionar `python` ou `pip` ao PATH.
   O inicializador não instala o Tesseract, o LibreTranslate ou modelos Argos.

   Se `.venv` já existir e tiver sido criado com outra versão do Python, renomeie
   a pasta para preservá-la antes de iniciar. Para criar e instalar manualmente:

   ```powershell
   py -3.13 -m venv .venv
   py -3.13 -m pip --python ".venv\Scripts\python.exe" install -r requirements.txt
   .\iniciar.bat
   ```

3. Use `http://127.0.0.1:5001` no navegador. Não abra `index.html`
   diretamente.

Por padrão, o servidor aceita conexões somente deste computador. Os arquivos do
projeto não são publicados; apenas a página, os recursos da interface e os
arquivos de exemplo ficam disponíveis pelo navegador.

O inicializador inicia o LibreTranslate local, se estiver instalado. O
aplicativo pode continuar sem ele e tenta Argos Translate como alternativa.
Mantenha aberta a janela do servidor do aplicativo; a janela do LibreTranslate
só é necessária enquanto esse mecanismo estiver sendo usado. Modelos Argos
instalados pelo próprio Argos são detectados automaticamente. O aplicativo não
baixa modelos Argos ao iniciar.
O Argos usa somente os recursos de tokenização incluídos nos pacotes locais e
não tenta atualizar o catálogo do Stanza durante a tradução. Pares sem os
arquivos locais necessários não são anunciados como disponíveis. Se uma
tradução direta produzir uma saída claramente inválida, o aplicativo tenta
outro caminho local entre os idiomas instalados.

Na seção “Modelos de tradução local”, o par de idiomas selecionado é comparado
com os modelos já instalados. “Consultar catálogo Argos” acessa a internet para
atualizar e verificar o catálogo; essa ação não baixa modelos de tradução.
Quando o catálogo confirma que um modelo está disponível, o botão de instalação
mostra o par e a origem. O download do modelo só começa depois de clicar em
“Instalar” e confirmar a solicitação.

## OCR para PDFs digitalizados

O programa verifica automaticamente páginas de PDF sem texto extraível e tenta
reconhecê-las com o Tesseract OCR. As dependências Python instaladas por
`requirements.txt` não incluem o executável Tesseract nem os dados de idioma.

### Instalar no Windows

1. Baixe o instalador de 64 bits recomendado na página do projeto Tesseract da
   Universidade de Mannheim:
   <https://github.com/UB-Mannheim/tesseract/wiki>.
2. Mantenha o diretório padrão sugerido pelo instalador
   (`C:\Program Files\Tesseract-OCR`) e selecione os dados de idioma português
   (`por`) na seção de idiomas adicionais. Se precisar de OCR em outros idiomas,
   selecione também os respectivos dados:

   - Português: `por`
   - Inglês: `eng`
   - Espanhol: `spa`

Se o instalador não oferecer `por`, obtenha `por.traineddata` do repositório
oficial <https://github.com/tesseract-ocr/tessdata_fast/blob/main/por.traineddata>
e coloque-o em
`C:\Program Files\Tesseract-OCR\tessdata\por.traineddata`. Não instale o
Tesseract dentro de uma pasta existente com outros arquivos: o desinstalador
do pacote pode remover toda a pasta de instalação.

### Verificar e iniciar

No PowerShell, confirme que o executável e o idioma estão disponíveis:

```powershell
$tesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
Test-Path $tesseract
& $tesseract --version
& $tesseract --list-langs
```

O resultado deve incluir `por`. O `app.py` localiza automaticamente o executável
no PATH ou no caminho padrão acima. Se instalou em outro local, configure a
variável antes de iniciar o aplicativo:

```powershell
$env:TESSERACT_CMD = "D:\caminho\Tesseract-OCR\tesseract.exe"
.\iniciar.bat
```

Depois de iniciar o aplicativo, abra
<http://127.0.0.1:5001/api/ocr/status?source_lang=pt>. Para confirmar o OCR
real — e não apenas a instalação — execute o teste que cria um PDF composto
somente por imagem, com palavras acentuadas, e chama o Tesseract sem mocks:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_app.TranslationApiTests.test_real_ocr_recognizes_portuguese_accents_in_scanned_pdf
```

Se Tesseract ou `por` estiver ausente, o teste será marcado como ignorado; isso
não significa que o OCR foi aprovado. A qualidade também depende da resolução
e da legibilidade do PDF digitalizado.

Para disponibilizar também o provedor opcional DeepL, configure a chave somente
no ambiente do sistema, nunca no HTML/JavaScript:

```powershell
$env:DEEPL_AUTH_KEY = "sua-chave"
$env:DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
$env:TRANSLATION_PROVIDERS = "libretranslate,argos,deepl"
.\iniciar.bat
```

Variáveis de configuração:

| Variável | Padrão | Finalidade |
|---|---|---|
| `TRANSLATION_PROVIDERS` | `libretranslate,argos,deepl` | Ordem dos mecanismos de fallback |
| `LIBRETRANSLATE_URL` | `http://localhost:5000,http://127.0.0.1:5000` | Um ou mais endpoints LibreTranslate separados por vírgula |
| `TRANSLATION_TIMEOUT_SECONDS` | `25` | Limite de conexão/resposta por chamada |
| `TRANSLATION_RETRIES` | `2` | Tentativas por mecanismo (máximo 3) |
| `TRANSLATION_TOTAL_TIMEOUT_SECONDS` | `300` | Prazo total da tradução (30 a 900 segundos) |
| `DEEPL_AUTH_KEY` | não configurada | Chave opcional do DeepL |
| `DEEPL_API_URL` | API Free do DeepL | Endpoint HTTPS opcional; HTTP só é aceito para host local |
| `TESSERACT_CMD` | PATH ou caminho padrão do Windows | Caminho opcional do executável Tesseract OCR |

Quando DeepL estiver habilitado, o texto extraído será enviado à API configurada;
não use esse provedor se o conteúdo não puder sair do computador.

O endpoint `GET /api/translation/status` informa mecanismos e pares de idiomas
detectados. `GET /api/health` verifica apenas se o aplicativo está ativo.

## Demonstração

Use “Carregar demonstração” na página e selecione PDF, DOCX ou PPTX. Esses
formatos são exemplos com resultados pré-preparados, não arquivos enviados para
tradução ao vivo. O envio para tradução continua aceitando somente PDF. A
demonstração permanece disponível quando os mecanismos de tradução estão desligados.

## Formatos e limitações

- Somente arquivos PDF podem ser enviados, com limite de 10 MB.
- Os downloads TXT, DOCX, PPTX e PDF preservam páginas/slides, títulos,
  parágrafos, listas e linhas de tabela quando identificados. São documentos
  reconstruídos; não prometem manter o tema, as imagens ou o posicionamento
  exato do arquivo original.
- O texto de tabelas é preservado em linhas/células, e as páginas/slides mantêm
  a separação. No PPTX, os blocos de texto são ordenados pela posição visual
  (de cima para baixo e da esquerda para a direita).
- PDFs compostos por imagens precisam do Tesseract e dos dados do idioma original
  para usar o OCR. Sem eles, o sistema informa o que está faltando.
- Imagens e elementos visuais não textuais não são traduzidos.

## Diagnóstico e testes

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Os testes verificam extração, validação, traduções, demonstração offline,
geração e leitura dos formatos de download, status dos modelos e o fluxo OCR
(o reconhecimento real é executado quando Tesseract e o idioma estão instalados).
O endpoint `GET /api/translation/status` ajuda a
identificar mecanismos indisponíveis ou pares de idiomas ausentes. As janelas e
os logs do `iniciar.bat`, Flask e LibreTranslate mostram falhas de inicialização.
