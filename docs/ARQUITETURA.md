# Arquitetura do TraduzEdu (MVC)

Este documento mostra como o código do **Tradutor de Aulas / TraduzEdu** está
organizado. Ele segue a documentação do TCC: interface em HTML + CSS +
JavaScript, processamento em Python, uma API de tradução e bibliotecas para ler
PDF, Word e PowerPoint.

## Padrão adotado

O projeto usa o padrão **MVC (Model-View-Controller)** nas duas camadas:

| Camada | Backend (Python/Flask) | Frontend (JavaScript) |
|---|---|---|
| **Model** | `traduzedu/models/`: estrutura do documento, idiomas, regras de texto | `static/js/model.js`: estado da tela e chamadas à API |
| **View** | `traduzedu/views/`: template HTML, CSS, JS e arquivos de exemplo | `static/js/view.js`: leitura e atualização do DOM |
| **Controller** | `traduzedu/controllers/`: rotas Flask (Blueprints) | `static/js/controller.js`: eventos da página |

Além disso, há uma camada de **Services** (`traduzedu/services/`), que faz o
trabalho pesado: extração, OCR, tradução e exportação. Os controllers só
validam a requisição, chamam os serviços e montam a resposta.

Outros padrões que já existiam no código ficaram explícitos:

- **Strategy + Chain of Responsibility**: os provedores de tradução
  (`LibreTranslateProvider`, `ArgosProvider` e `DeepLProvider`) têm a mesma
  interface (`supports`, `translate`, `status`). O `TranslationEngine` tenta um
  de cada vez até um deles responder.
- **Application Factory**: `create_app()` monta a aplicação Flask, o que
  facilita os testes.
- **Blueprints**: cada controller é um módulo independente de rotas.

## Estrutura de pastas

```
TccYas/
├── app.py                      # ponto de entrada (python app.py / iniciar.bat)
├── iniciar.bat
├── requirements.txt
├── traduzedu/
│   ├── __init__.py             # create_app()
│   ├── config.py               # limites e variáveis de ambiente
│   ├── models/
│   │   ├── document.py         # página/bloco, validação para download
│   │   ├── language.py         # idiomas suportados (pt, en, es)
│   │   └── text.py             # limpeza e divisão do texto em trechos
│   ├── services/
│   │   ├── extraction.py       # leitura de PDF, DOCX e PPTX
│   │   ├── ocr.py              # Tesseract para PDFs digitalizados
│   │   ├── translation.py      # tradução dos blocos preservando a estrutura
│   │   ├── translation_engine.py  # provedores e fallback
│   │   └── export.py           # geração de TXT, DOCX, PPTX e PDF
│   ├── controllers/
│   │   ├── pages_controller.py        # GET /
│   │   ├── translation_controller.py  # /api/translate, /api/translation/status, /api/health, /api/demo
│   │   ├── download_controller.py     # /api/download/<formato>
│   │   └── resources_controller.py    # /api/ocr/status, /api/argos/*
│   ├── views/
│   │   ├── templates/index.html
│   │   └── static/
│   │       ├── css/style.css
│   │       ├── js/model.js, view.js, controller.js
│   │       └── exemplos/sample.pdf, sample.docx, sample.pptx
│   └── data/                   # demo_results.json (demonstração offline)
├── tests/
│   ├── test_app.py
│   └── test_translation_engine.py
└── docs/ARQUITETURA.md
```

## Fluxo do sistema

Corresponde ao fluxograma (seção 8) e às funcionalidades da seção 7 da
documentação:

```
Professor (View)
   │ 1. escolhe o arquivo e os idiomas            -> controller.js / view.js
   ▼
POST /api/translate                                -> translation_controller
   │ 2. valida formato, tamanho e idiomas         -> models/language.py
   │ 3. extrai o texto em blocos                  -> services/extraction.py (+ ocr.py)
   │ 4. traduz bloco a bloco, em lotes            -> services/translation.py
   │                                                 └─ translation_engine.py (API)
   ▼
JSON com páginas e blocos                          -> models/document.py
   │ 5. visualização por página/slide             -> view.js
   ▼
POST /api/download/<formato>                       -> download_controller
   │ 6. valida e gera o arquivo                   -> models/document.py + services/export.py
   ▼
Arquivo traduzido baixado pelo professor
```

## Preservação da estrutura (seção 3.3)

A documentação aponta que o conteúdo traduzido "é apresentado junto, sem manter
a organização original". Por isso, o model `document.py` define quatro tipos de
bloco: `heading`, `paragraph`, `list-item` e `table-row`. A extração classifica
cada trecho, a tradução mantém a ordem e o tipo, e a visualização e os
exportadores usam esses tipos para reconstruir títulos, listas e tabelas.

## Onde mexer para…

| Tarefa | Arquivo |
|---|---|
| Aceitar DOCX/PPTX no envio | `config.ALLOWED_UPLOAD_EXTENSIONS`, mensagem em `translation_controller._validate_upload`, `EXTENSOES_PERMITIDAS` em `model.js` e `accept` do `<input>` |
| Adicionar um idioma | `models/language.py` e os `<select>` de `index.html` |
| Adicionar um provedor de tradução | nova classe em `services/translation_engine.py` e registro em `TranslationEngine.from_environment` |
| Novo formato de download | `services/export.py` (`export_document`) e `config.EXPORT_FORMATS` |
| Mudar textos e visual da página | `views/templates/index.html` e `views/static/css/style.css` |
