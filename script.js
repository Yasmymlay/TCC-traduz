// =====================================
// ELEMENTOS DO SITE
// =====================================

const arquivoInput = document.getElementById("arquivo");
const arquivoSelecionado = document.getElementById("arquivoSelecionado");
const btnTraduzir = document.getElementById("btnTraduzir");
const resultado = document.getElementById("resultado");
const mensagem = document.getElementById("mensagem");

const nomeResultado = document.getElementById("nomeResultado");
const formatoResultado = document.getElementById("formatoResultado");
const idiomaResultado = document.getElementById("idiomaResultado");
const modoResultado = document.getElementById("modoResultado");

const visualizacao = document.getElementById("visualizacao");

const btnBaixar = document.getElementById("btnBaixar");
const btnNovo = document.getElementById("btnNovo");

// Elementos dos slides
const slideNumero = document.getElementById("slideNumero");
const slideTitulo = document.getElementById("slideTitulo");
const slideConteudo = document.getElementById("slideConteudo");
const contadorSlide = document.getElementById("contadorSlide");
const slideAnterior = document.getElementById("slideAnterior");
const slideProximo = document.getElementById("slideProximo");

// =====================================
// VARIÁVEIS
// =====================================

let arquivoAtual = null;
let textoExtraido = "";
let textoTraduzido = "";
let slides = [];
let slideAtual = 0;
let idiomaAtivo = "pt";

// =====================================
// TRADUÇÃO DA INTERFACE
// =====================================

const textosInterface = {
    pt: {
        "nav.inicio": "Início",
        "nav.traduzir": "Traduzir",
        "nav.resultado": "Resultado",
        "nav.sobre": "Sobre",
        "hero.tag": "✨ Aprendizado sem fronteiras",
        "hero.title.line1": "Traduza seus materiais",
        "hero.title.line2": "de estudo",
        "hero.description": "Transforme PDFs, documentos Word e apresentações em materiais traduzidos de forma simples, rápida e organizada.",
        "hero.button": "Começar tradução",
        "sectionTranslation.tag": "ÁREA DE TRADUÇÃO",
        "sectionTranslation.title": "Traduza seu material",
        "sectionTranslation.description": "Envie seu arquivo e configure a tradução de acordo com suas necessidades.",
        "upload.title": "Carregar arquivo",
        "upload.description": "Escolha o material que deseja traduzir.",
        "upload.buttonLabel": "Escolher arquivo",
        "upload.dragText": "Arraste seu arquivo ou clique aqui",
        "upload.supportedFiles": "PDF, Word ou PowerPoint • Máx. 10MB",
        "languages.title": "Idiomas",
        "languages.description": "Selecione o idioma original e o idioma de destino.",
        "languages.originLabel": "Idioma original",
        "languages.targetLabel": "Traduzir para",
        "mode.complete.title": "Tradução completa",
        "mode.complete.description": "Traduz todo o conteúdo do arquivo.",
        "mode.pages.title": "Tradução por páginas",
        "mode.pages.description": "Traduz apenas as páginas selecionadas.",
        "mode.chapters.title": "Tradução por capítulos",
        "mode.chapters.description": "Traduz somente os capítulos selecionados.",
        "button.translate": "Traduzir agora",
        "message.default": "Selecione um arquivo e configure os idiomas para começar.",
        "about.tag": "SOBRE O PROJETO",
        "about.title": "Aprendizado sem fronteiras",
        "about.description": "O Tradutor de Aulas foi desenvolvido para facilitar o acesso a materiais educacionais em diferentes idiomas, tornando o processo de aprendizagem mais simples e acessível.",
        "about.benefit1": "Materiais educacionais",
        "about.benefit2": "Vários idiomas",
        "about.benefit3": "Processo simples",
        "footer.brand": "🎓 Tradutor de Aulas",
        "footer.tagline": "Aprendizado sem fronteiras",
        "option.pt": "Português",
        "option.en": "Inglês",
        "option.es": "Espanhol",
        "empty.file": "Nenhum arquivo selecionado",
        "status.file.selected": "Arquivo selecionado"
    },

    en: {
        "nav.inicio": "Home",
        "nav.traduzir": "Translate",
        "nav.resultado": "Result",
        "nav.sobre": "About",
        "hero.tag": "✨ Borderless learning",
        "hero.title.line1": "Translate your study",
        "hero.title.line2": "materials",
        "hero.description": "Transform PDFs, Word documents and presentations into translated learning materials in a simple, fast and organized way.",
        "hero.button": "Start translation",
        "sectionTranslation.tag": "TRANSLATION AREA",
        "sectionTranslation.title": "Translate your material",
        "sectionTranslation.description": "Upload your file and configure the translation according to your needs.",
        "upload.title": "Upload file",
        "upload.description": "Choose the file you want to translate.",
        "upload.buttonLabel": "Choose file",
        "upload.dragText": "Drag and drop your file or click here",
        "upload.supportedFiles": "PDF, Word or PowerPoint • Max. 10MB",
        "languages.title": "Languages",
        "languages.description": "Select the source language and the target language.",
        "languages.originLabel": "Source language",
        "languages.targetLabel": "Translate to",
        "mode.complete.title": "Full translation",
        "mode.complete.description": "Translates the entire file.",
        "mode.pages.title": "Page-by-page translation",
        "mode.pages.description": "Translates only selected pages.",
        "mode.chapters.title": "Chapter-by-chapter translation",
        "mode.chapters.description": "Translates only selected chapters.",
        "button.translate": "Translate now",
        "message.default": "Select a file and configure the languages to get started.",
        "about.tag": "ABOUT THE PROJECT",
        "about.title": "Borderless learning",
        "about.description": "Tradutor de Aulas was developed to make educational materials more accessible across different languages.",
        "about.benefit1": "Educational materials",
        "about.benefit2": "Multiple languages",
        "about.benefit3": "Simple process",
        "footer.brand": "🎓 Tradutor de Aulas",
        "footer.tagline": "Borderless learning",
        "option.pt": "Portuguese",
        "option.en": "English",
        "option.es": "Spanish",
        "empty.file": "No file selected",
        "status.file.selected": "File selected"
    },

    es: {
        "nav.inicio": "Inicio",
        "nav.traduzir": "Traducir",
        "nav.resultado": "Resultado",
        "nav.sobre": "Sobre",
        "hero.tag": "✨ Aprendizaje sin fronteras",
        "hero.title.line1": "Traduce tus materiales",
        "hero.title.line2": "de estudio",
        "hero.description": "Transforma PDFs, documentos de Word y presentaciones en materiales traducidos de forma simple, rápida y organizada.",
        "hero.button": "Comenzar traducción",
        "sectionTranslation.tag": "ÁREA DE TRADUCCIÓN",
        "sectionTranslation.title": "Traduce tu material",
        "sectionTranslation.description": "Sube tu archivo y configura la traducción según tus necesidades.",
        "upload.title": "Cargar archivo",
        "upload.description": "Elige el material que deseas traducir.",
        "upload.buttonLabel": "Elegir archivo",
        "upload.dragText": "Arrastra tu archivo o haz clic aquí",
        "upload.supportedFiles": "PDF, Word o PowerPoint • Máx. 10MB",
        "languages.title": "Idiomas",
        "languages.description": "Selecciona el idioma de origen y el idioma de destino.",
        "languages.originLabel": "Idioma de origen",
        "languages.targetLabel": "Traducir a",
        "mode.complete.title": "Traducción completa",
        "mode.complete.description": "Traduce todo el contenido del archivo.",
        "mode.pages.title": "Traducción por páginas",
        "mode.pages.description": "Traduce solo las páginas seleccionadas.",
        "mode.chapters.title": "Traducción por capítulos",
        "mode.chapters.description": "Traduce solo los capítulos seleccionados.",
        "button.translate": "Traducir ahora",
        "message.default": "Selecciona un archivo y configura los idiomas para comenzar.",
        "about.tag": "SOBRE EL PROYECTO",
        "about.title": "Aprendizaje sin fronteras",
        "about.description": "Tradutor de Aulas fue desarrollado para facilitar el acceso a materiales educativos en diferentes idiomas.",
        "about.benefit1": "Materiales educativos",
        "about.benefit2": "Varios idiomas",
        "about.benefit3": "Proceso simple",
        "footer.brand": "🎓 Tradutor de Aulas",
        "footer.tagline": "Aprendizaje sin fronteras",
        "option.pt": "Portugués",
        "option.en": "Inglés",
        "option.es": "Español",
        "empty.file": "Ningún archivo seleccionado",
        "status.file.selected": "Archivo seleccionado"
    }
};

// =====================================
// IDIOMA DA INTERFACE
// =====================================

function getTextoInterface(lang, chave) {
    return textosInterface[lang]?.[chave]
        || textosInterface.pt[chave]
        || chave;
}

function aplicarIdiomaInterface(lang = "pt") {
    idiomaAtivo = lang;
    document.documentElement.lang = lang;

    document.querySelectorAll("[data-i18n]").forEach((elemento) => {
        const chave = elemento.dataset.i18n;
        const valor = getTextoInterface(lang, chave);

        if (valor) {
            elemento.textContent = valor;
        }
    });

    const origem = document.getElementById("idiomaOrigem");
    const destino = document.getElementById("idiomaDestino");

    [
        { select: origem, key: "option.pt", value: "pt" },
        { select: origem, key: "option.en", value: "en" },
        { select: origem, key: "option.es", value: "es" },
        { select: destino, key: "option.pt", value: "pt" },
        { select: destino, key: "option.en", value: "en" },
        { select: destino, key: "option.es", value: "es" }
    ].forEach(({ select, key, value }) => {
        if (!select) return;

        const option = select.querySelector(
            `option[value="${value}"]`
        );

        if (option) {
            option.textContent = getTextoInterface(lang, key);
        }
    });

    const botao = document.getElementById("btnTraduzir");

    if (botao) {
        botao.innerHTML =
            "<span>✨</span>" +
            getTextoInterface(lang, "button.translate") +
            "<span>→</span>";
    }

    const mensagemAtual = document.getElementById("mensagem");

    if (
        mensagemAtual &&
        mensagemAtual.dataset.i18n === "message.default"
    ) {
        mensagemAtual.textContent =
            getTextoInterface(lang, "message.default");
    }
}

document.querySelectorAll(".idioma-selector button").forEach((botao) => {
    botao.addEventListener("click", () => {
        document.querySelectorAll(".idioma-selector button").forEach((item) => {
            item.classList.remove("active");
        });

        botao.classList.add("active");
        aplicarIdiomaInterface(botao.dataset.lang || "pt");
    });
});

aplicarIdiomaInterface("pt");

// =====================================
// SELEÇÃO DO ARQUIVO
// =====================================

if (arquivoInput) {
    arquivoInput.addEventListener("change", function () {
        arquivoAtual = this.files[0];

        if (!arquivoAtual) {
            if (arquivoSelecionado) {
                arquivoSelecionado.textContent =
                    getTextoInterface(idiomaAtivo, "empty.file");
            }
            return;
        }

        const extensao = arquivoAtual.name
            .split(".")
            .pop()
            .toLowerCase();

        const formatosPermitidos = ["pdf", "docx", "pptx"];

        if (!formatosPermitidos.includes(extensao)) {
            if (arquivoSelecionado) {
                arquivoSelecionado.textContent =
                    "❌ Formato não permitido.";
            }

            arquivoAtual = null;
            this.value = "";
            return;
        }

        if (arquivoSelecionado) {
            arquivoSelecionado.innerHTML =
                `📄 <strong>${escaparHTML(arquivoAtual.name)}</strong>`;
        }

        const uploadArea = document.querySelector(".upload-area");

        if (uploadArea) {
            uploadArea.classList.add("is-filled");
        }

        mostrarMensagem(
            "✅ " +
            getTextoInterface(idiomaAtivo, "status.file.selected") +
            "."
        );
    });
}

// =====================================
// BOTÃO TRADUZIR
// =====================================

if (btnTraduzir) {
    btnTraduzir.addEventListener("click", async function () {
        if (!arquivoAtual) {
            mostrarMensagem("⚠️ Primeiro selecione um arquivo.", true);
            return;
        }

        const origemElement = document.getElementById("idiomaOrigem");
        const destinoElement = document.getElementById("idiomaDestino");

        if (!origemElement || !destinoElement) {
            mostrarMensagem("❌ Campos de idioma não encontrados.", true);
            return;
        }

        const origem = origemElement.value;
        const destino = destinoElement.value;

        btnTraduzir.disabled = true;
        btnTraduzir.textContent = "⏳ Processando...";

        try {
            const extensao = arquivoAtual.name
                .split(".")
                .pop()
                .toLowerCase();

            mostrarMensagem("📖 Lendo o material...");

            if (extensao === "pdf") {
                textoExtraido = await lerPDF(arquivoAtual);
            } else if (extensao === "docx") {
                textoExtraido = await lerWord(arquivoAtual);
            } else if (extensao === "pptx") {
                textoExtraido = await lerPowerPoint(arquivoAtual);
            } else {
                throw new Error("Formato de arquivo não suportado.");
            }

            if (!textoExtraido || !textoExtraido.trim()) {
                throw new Error("Não foi encontrado texto no arquivo.");
            }

            mostrarMensagem("🌐 Traduzindo o conteúdo...");

            textoTraduzido = await traduzirTexto(
                textoExtraido,
                origem,
                destino
            );

            if (!textoTraduzido || !textoTraduzido.trim()) {
                throw new Error("A tradução não retornou nenhum texto.");
            }

            mostrarResultado(arquivoAtual, origem, destino, textoTraduzido);
            mostrarMensagem("✅ Tradução concluída!");

        } catch (erro) {
            console.error("Erro na tradução:", erro);
            mostrarMensagem(
                "❌ Não foi possível concluir: " + erro.message,
                true
            );
        } finally {
            btnTraduzir.disabled = false;
            aplicarIdiomaInterface(idiomaAtivo);
        }
    });
}