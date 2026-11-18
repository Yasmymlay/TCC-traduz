# Tradutor de Aulas (TraduzEdu)

Aplicação local Flask para extrair texto de arquivos PDF, traduzir para
português, inglês ou espanhol e visualizar/baixar o resultado em TXT, DOCX,
PPTX ou PDF.

O envio para tradução aceita somente arquivos PDF. O download padrão é o
**próprio PDF traduzido, com o mesmo layout**: fundos, imagens, cores e
posições ficam iguais e só o texto muda. Também é possível baixar só o texto
em PDF, DOCX, PPTX ou TXT.

## Organização do código (MVC)

O código está no pacote `traduzedu/`, organizado em Model-View-Controller:

- `traduzedu/models/`: estrutura do documento, idiomas e regras de texto
- `traduzedu/views/`: `templates/index.html` e `static/` (CSS, JS e exemplos)
- `traduzedu/controllers/`: rotas Flask (Blueprints)
- `traduzedu/services/`: extração, OCR, tradução e exportação

O frontend segue a mesma divisão: `static/js/model.js`, `view.js` e
`controller.js`. Os detalhes e o fluxo completo estão em
[docs/ARQUITETURA.md](docs/ARQUITETURA.md).

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
O servidor do aplicativo roda numa janela minimizada "Tradutor de Aulas"; mantenha-a
aberta. As mensagens do servidor vão para `logs\servidor.log` (e não para a janela),
então clicar na janela não congela mais o servidor. A janela do LibreTranslate
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

O resultado deve incluir `por`. O aplicativo (`traduzedu/services/ocr.py`) localiza automaticamente o executável
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
.\.venv\Scripts\python.exe -m unittest -v tests.test_app.TranslationApiTests.test_real_ocr_recognizes_portuguese_accents_in_scanned_pdf
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

Use “Carregar demonstração” na página para ver o PDF de exemplo
(`traduzedu/views/static/exemplos/sample.pdf`) já traduzido para o espanhol. O
resultado fica pronto em `traduzedu/data/demo_results.json`, então a demonstração
funciona mesmo com os mecanismos de tradução desligados. “Baixar arquivo de
exemplo” baixa o PDF original para testar a tradução de verdade.

## Formatos e limitações

- Somente arquivos PDF podem ser enviados, com limite de 10 MB.
- “PDF traduzido (mesmo layout)” troca o texto no próprio PDF enviado. Texto
  que faz parte de uma imagem (rótulos desenhados, páginas digitalizadas) não é
  trocado, e uma tradução mais longa que o original pode usar uma fonte um pouco
  menor para caber. O arquivo fica disponível por 1 hora depois da tradução.
- Os downloads “PDF só com o texto”, DOCX, PPTX e TXT preservam páginas/slides, títulos,
  parágrafos, listas e linhas de tabela quando identificados. São documentos
  reconstruídos; não prometem manter o tema, as imagens ou o posicionamento
  exato do arquivo original.
- O texto de tabelas é preservado em linhas/células, e as páginas/slides mantêm
  a separação. No PPTX, os blocos de texto são ordenados pela posição visual
  (de cima para baixo e da esquerda para a direita).
- PDFs compostos por imagens precisam do Tesseract e dos dados do idioma original
  para usar o OCR. Sem eles, páginas sem texto selecionável ficam sem tradução e
  o sistema avisa quais foram; se nenhuma página tiver texto, a tradução é recusada
  com a explicação do que está faltando.
- Imagens e elementos visuais não textuais não são traduzidos.

## Problemas comuns

- **"O tempo de espera da tradução foi excedido"**: quase sempre é um servidor
  antigo travado ocupando a porta 5001. Feche a janela "Tradutor de Aulas" (ou
  encerre o processo `python` no Gerenciador de Tarefas) e execute `iniciar.bat`
  de novo. O inicializador e o `app.py` agora avisam quando a porta está ocupada.
- **"Todos os mecanismos configurados falharam"**: nenhum tradutor está
  instalado. Em “Modelos de tradução local”, escolha o par (por exemplo,
  Português → Espanhol), clique em “Consultar catálogo Argos” e depois em
  “Instalar”. O download é feito uma vez só.
- Detalhes de erros do servidor ficam em `logs\servidor.log`.

## Diagnóstico e testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v -s tests -t .
```

Os testes verificam extração, validação, traduções, demonstração offline,
geração e leitura dos formatos de download, status dos modelos e o fluxo OCR
(o reconhecimento real é executado quando Tesseract e o idioma estão instalados).
O endpoint `GET /api/translation/status` ajuda a
identificar mecanismos indisponíveis ou pares de idiomas ausentes. As janelas e
os logs do `iniciar.bat`, Flask e LibreTranslate mostram falhas de inicialização.
