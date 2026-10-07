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


// =====================================
// ELEMENTOS DOS SLIDES
// =====================================
// São opcionais.
// Seu HTML pode não ter esses elementos,
// e o sistema continuará funcionando.

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
// VERIFICAÇÃO DOS ELEMENTOS
// =====================================

if (!arquivoInput) {
    console.error("Elemento #arquivo não encontrado.");
}

if (!btnTraduzir) {
    console.error("Elemento #btnTraduzir não encontrado.");
}


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
        "upload.description": "Choose the material you want to translate.",
        "upload.buttonLabel": "Choose file",
        "upload.dragText": "Drag and drop your file or click here",
        "upload.supportedFiles": "PDF, Word or PowerPoint • Max. 10MB",
        "languages.title": "Languages",
        "languages.description": "Select the source language and the target language.",
        "languages.originLabel": "Source language",
        "languages.targetLabel": "Translate to",
        "mode.complete.title": "Full translation",
        "mode.complete.description": "Translates the entire file content.",
        "mode.pages.title": "Page-by-page translation",
        "mode.pages.description": "Translates only the selected pages.",
        "mode.chapters.title": "Chapter-by-chapter translation",
        "mode.chapters.description": "Translates only the selected chapters.",
        "button.translate": "Translate now",
        "message.default": "Select a file and configure the languages to get started.",
        "about.tag": "ABOUT THE PROJECT",
        "about.title": "Borderless learning",
        "about.description": "The Tradutor de Aulas was developed to make educational materials more accessible across different languages, making the learning process simpler and more inclusive.",
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
        "about.description": "Tradutor de Aulas fue desarrollado para facilitar el acceso a materiales educativos en diferentes idiomas, haciendo que el proceso de aprendizaje sea más simple y accesible.",
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
        if (!select) {
            return;
        }

        const option = select.querySelector(`option[value="${value}"]`);

        if (option) {
            option.textContent = getTextoInterface(lang, key);
        }
    });

    const btnTraduzir = document.getElementById("btnTraduzir");

    if (btnTraduzir) {
        btnTraduzir.innerHTML =
            '<span>✨</span>' +
            getTextoInterface(lang, "button.translate") +
            '<span>→</span>';
    }

    const mensagem = document.getElementById("mensagem");

    if (mensagem && mensagem.dataset.i18n === "message.default") {
        mensagem.textContent = getTextoInterface(lang, "message.default");
    }
}

const botoesIdioma = document.querySelectorAll(
    ".idioma-selector button"
);

botoesIdioma.forEach((botao) => {

    botao.addEventListener("click", () => {

        botoesIdioma.forEach((b) => {
            b.classList.remove("active");
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

            arquivoSelecionado.textContent =
                getTextoInterface(idiomaAtivo, "empty.file");

            return;
        }


        const extensao = arquivoAtual.name
            .split(".")
            .pop()
            .toLowerCase();


        const formatosPermitidos = [
            "pdf",
            "docx",
            "pptx"
        ];


        if (!formatosPermitidos.includes(extensao)) {

            arquivoSelecionado.textContent =
                "❌ Formato não permitido.";

            arquivoAtual = null;

            this.value = "";

            return;
        }


        arquivoSelecionado.innerHTML =
            `📄 <strong>${escaparHTML(arquivoAtual.name)}</strong>`;

        const uploadArea =
            document.querySelector(".upload-area");

        if (uploadArea) {
            uploadArea.classList.add("is-filled");
        }

        mostrarMensagem(
            "✅ " + getTextoInterface(idiomaAtivo, "status.file.selected") + "."
        );

    });

}


// =====================================
// BOTÃO TRADUZIR
// =====================================

if (btnTraduzir) {

    btnTraduzir.addEventListener(
        "click",
        async function () {

            if (!arquivoAtual) {

                mostrarMensagem(
                    "⚠️ Primeiro selecione um arquivo.",
                    true
                );

                return;
            }


            const origemElement =
                document.getElementById("idiomaOrigem");

            const destinoElement =
                document.getElementById("idiomaDestino");


            if (!origemElement || !destinoElement) {

                mostrarMensagem(
                    "❌ Campos de idioma não encontrados.",
                    true
                );

                return;
            }


            const origem = origemElement.value;
            const destino = destinoElement.value;


            btnTraduzir.disabled = true;

            btnTraduzir.textContent =
                "⏳ Processando...";


            try {

                const extensao =
                    arquivoAtual.name
                        .split(".")
                        .pop()
                        .toLowerCase();


                // =================================
                // LER ARQUIVO
                // =================================

                mostrarMensagem(
                    "📖 Lendo o material..."
                );


                if (extensao === "pdf") {

                    textoExtraido =
                        await lerPDF(arquivoAtual);

                }

                else if (extensao === "docx") {

                    textoExtraido =
                        await lerWord(arquivoAtual);

                }

                else if (extensao === "pptx") {

                    textoExtraido =
                        await lerPowerPoint(arquivoAtual);

                }

                else {

                    throw new Error(
                        "Formato de arquivo não suportado."
                    );

                }


                if (!textoExtraido || !textoExtraido.trim()) {

                    throw new Error(
                        "Não foi encontrado texto no arquivo."
                    );

                }


                // =================================
                // TRADUZIR
                // =================================

                mostrarMensagem(
                    "🌎 Traduzindo o material..."
                );


                textoTraduzido =
                    await traduzirTexto(
                        textoExtraido,
                        origem,
                        destino
                    );


                if (!textoTraduzido || !textoTraduzido.trim()) {

                    throw new Error(
                        "A tradução não retornou conteúdo."
                    );

                }


                // =================================
                // MOSTRAR RESULTADO
                // =================================

                mostrarResultado();


                mostrarMensagem(
                    "✅ Material traduzido com sucesso!"
                );

            }

            catch (erro) {

                console.error(
                    "ERRO:",
                    erro
                );


                mostrarMensagem(
                    "❌ " + erro.message,
                    true
                );

            }

            finally {

                btnTraduzir.disabled = false;

                btnTraduzir.innerHTML =
                    '<span>✨</span>' +
                    getTextoInterface(idiomaAtivo, "button.translate") +
                    '<span>→</span>';

            }

        }
    );

}


// =====================================
// TRADUÇÃO COM LIBRETRANSLATE
// =====================================

function normalizarCodigoIdioma(codigo) {

    const mapa = {
        "pt": "pt",
        "pt-br": "pt",
        "portugues": "pt",
        "portuguese": "pt",
        "en": "en",
        "eng": "en",
        "english": "en",
        "es": "es",
        "esp": "es",
        "espanhol": "es",
        "spanish": "es"
    };

    return mapa[
        String(codigo || "")
            .trim()
            .toLowerCase()
    ] || String(codigo || "")
        .trim()
        .toLowerCase();

}

async function traduzirTextoComFallback(
    texto,
    origem,
    destino
) {

    const tentativas = [

        async () => {

            const resposta =
                await fetch(
                    "http://127.0.0.1:5000/translate",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/x-www-form-urlencoded"
                        },
                        body:
                            new URLSearchParams({
                                q: texto,
                                source: origem,
                                target: destino,
                                format: "text"
                            }).toString()
                    }
                );

            if (!resposta.ok) {
                throw new Error(
                    `Erro do LibreTranslate. Código: ${resposta.status}`
                );
            }

            const resultadoAPI =
                await resposta.json();

            if (resultadoAPI.error) {
                throw new Error(
                    resultadoAPI.error
                );
            }

            if (!resultadoAPI.translatedText) {
                throw new Error(
                    "O LibreTranslate não retornou a tradução."
                );
            }

            return resultadoAPI.translatedText;

        },

        async () => {

            const url =
                `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${origem}&tl=${destino}&dt=t&ie=UTF-8&oe=UTF-8&q=${encodeURIComponent(texto)}`;

            const resposta =
                await fetch(url);

            if (!resposta.ok) {
                throw new Error(
                    `Erro do Google Translate. Código: ${resposta.status}`
                );
            }

            const resultadoAPI =
                await resposta.json();

            if (
                !Array.isArray(resultadoAPI) ||
                !Array.isArray(resultadoAPI[0])
            ) {
                throw new Error(
                    "Resposta inválida do Google Translate."
                );
            }

            return resultadoAPI[0]
                .map((item) => item[0] || "")
                .join("");

        }

    ];

    let ultimoErro = null;

    for (const tentar of tentativas) {

        try {

            return await tentar();

        }

        catch (erro) {

            ultimoErro = erro;

        }

    }

    throw new Error(
        ultimoErro?.message ||
        "Não foi possível traduzir o texto."
    );

}

async function traduzirTexto(
    texto,
    origem,
    destino
) {

    origem = normalizarCodigoIdioma(origem);
    destino = normalizarCodigoIdioma(destino);

    // =====================================
    // MESMO IDIOMA
    // =====================================

    if (origem === destino) {
        return texto;
    }


    const extensao =
        arquivoAtual.name
            .split(".")
            .pop()
            .toLowerCase();


    let blocos = [];


    // =====================================
    // POWERPOINT
    // =====================================

    if (extensao === "pptx") {

        blocos = texto
            .split(
                /(?=---\s*(?:\*?\s*)Slide\s+\d+\s*(?:\*?\s*)---)/i
            )
            .filter(
                bloco =>
                    bloco.trim().length > 0
            );

    }


    // =====================================
    // PDF
    // =====================================

    else if (extensao === "pdf") {

        blocos = texto
            .split(
                /(?=---\s*(?:\*?\s*)Página\s+\d+\s*(?:\*?\s*)---)/i
            )
            .filter(
                bloco =>
                    bloco.trim().length > 0
            );

    }


    // =====================================
    // WORD
    // =====================================

    else {

        blocos = [texto];

    }


    const traducoes = [];


    // =====================================
    // TRADUZIR BLOCO POR BLOCO
    // =====================================

    for (
        let i = 0;
        i < blocos.length;
        i++
    ) {

        let bloco =
            blocos[i].trim();


        let marcador = "";


        // =================================
        // PRESERVAR MARCADOR
        // =================================

        if (
            extensao === "pptx" ||
            extensao === "pdf"
        ) {

            const encontrado =
                bloco.match(
                    /^---\s*(?:\*?\s*)?(Slide|Página)\s+\d+\s*(?:\*?\s*)?---/i
                );


            if (encontrado) {

                marcador =
                    encontrado[0];

                bloco =
                    bloco
                        .substring(
                            marcador.length
                        )
                        .trim();

            }

        }


        // =================================
        // BLOCO VAZIO
        // =================================

        if (!bloco) {

            traducoes.push(
                marcador
            );

            continue;
        }


        const tipoMaterial =
            extensao === "pptx"
                ? "slide"
                : extensao === "pdf"
                    ? "página"
                    : "conteúdo";


        mostrarMensagem(
            `🌎 Traduzindo ${tipoMaterial} ${i + 1} de ${blocos.length}...`
        );


        // =================================
        // DIVIDIR TEXTO GRANDE
        // =================================

        const tamanhoMaximo = 3000;

        const partes = [];


        for (
            let inicio = 0;
            inicio < bloco.length;
            inicio += tamanhoMaximo
        ) {

            partes.push(
                bloco.substring(
                    inicio,
                    inicio + tamanhoMaximo
                )
            );

        }


        const partesTraduzidas = [];


        // =================================
        // TRADUZIR CADA PARTE
        // =================================

        for (
            let j = 0;
            j < partes.length;
            j++
        ) {

            const dados =
                new URLSearchParams();


            dados.append(
                "q",
                partes[j]
            );


            dados.append(
                "source",
                origem
            );


            dados.append(
                "target",
                destino
            );


            dados.append(
                "format",
                "text"
            );


            let textoTraduzidoParcial;


            try {

                textoTraduzidoParcial =
                    await traduzirTextoComFallback(
                        partes[j],
                        origem,
                        destino
                    );

            }

            catch (erro) {

                throw new Error(
                    "Não foi possível realizar a tradução. Verifique a conexão e o serviço de idioma."
                );

            }


            partesTraduzidas.push(
                textoTraduzidoParcial
            );

        }


        const blocoTraduzido =
            partesTraduzidas.join(
                "\n\n"
            );


        // =================================
        // RECOLOCAR MARCADOR
        // =================================

        if (marcador) {

            traducoes.push(
                marcador +
                "\n\n" +
                blocoTraduzido
            );

        }

        else {

            traducoes.push(
                blocoTraduzido
            );

        }

    }


    // =====================================
    // RESULTADO FINAL
    // =====================================

    return traducoes.join(
        "\n\n"
    );

}


// =====================================
// LER PDF
// =====================================

async function lerPDF(arquivo) {

    const arrayBuffer =
        await arquivo.arrayBuffer();


    const pdfjsLib =
        await import(
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs"
        );


    pdfjsLib.GlobalWorkerOptions.workerSrc =
        "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs";


    const pdf =
        await pdfjsLib.getDocument({
            data: arrayBuffer
        }).promise;


    let texto = "";


    for (
        let pagina = 1;
        pagina <= pdf.numPages;
        pagina++
    ) {

        const page =
            await pdf.getPage(
                pagina
            );


        const content =
            await page.getTextContent();


        const linhas =
            content.items
                .map(
                    item =>
                        item.str
                )
                .join(" ");


        texto +=
            `\n\n--- Página ${pagina} ---\n\n`;


        texto +=
            linhas;

    }


    return texto.trim();

}


// =====================================
// LER WORD
// =====================================

async function lerWord(arquivo) {

    if (typeof mammoth === "undefined") {

        throw new Error(
            "A biblioteca Mammoth não foi carregada."
        );

    }


    const arrayBuffer =
        await arquivo.arrayBuffer();


    const resultadoWord =
        await mammoth.extractRawText({
            arrayBuffer: arrayBuffer
        });


    return resultadoWord.value.trim();

}


// =====================================
// LER POWERPOINT
// =====================================

async function lerPowerPoint(arquivo) {

    if (typeof JSZip === "undefined") {

        throw new Error(
            "A biblioteca JSZip não foi carregada."
        );

    }


    const arrayBuffer =
        await arquivo.arrayBuffer();


    const zip =
        await JSZip.loadAsync(
            arrayBuffer
        );


    let texto = "";


    const arquivos =
        Object.keys(
            zip.files
        );


    const slidesArquivo =
        arquivos
            .filter(
                nome =>
                    /^ppt\/slides\/slide\d+\.xml$/
                        .test(nome)
            )
            .sort(
                (a, b) => {

                    const numeroA =
                        parseInt(
                            a.match(
                                /slide(\d+)/
                            )[1]
                        );


                    const numeroB =
                        parseInt(
                            b.match(
                                /slide(\d+)/
                            )[1]
                        );


                    return numeroA - numeroB;

                }
            );


    if (slidesArquivo.length === 0) {

        throw new Error(
            "Nenhum slide foi encontrado no PowerPoint."
        );

    }


    for (
        let i = 0;
        i < slidesArquivo.length;
        i++
    ) {

        const nomeSlide =
            slidesArquivo[i];


        const conteudo =
            await zip.files[
                nomeSlide
            ].async("text");


        const parser =
            new DOMParser();


        const xml =
            parser.parseFromString(
                conteudo,
                "application/xml"
            );


        const elementos =
            xml.getElementsByTagName(
                "a:t"
            );


        let textoSlide = "";


        for (
            let j = 0;
            j < elementos.length;
            j++
        ) {

            textoSlide +=
                elementos[j].textContent +
                " ";

        }


        texto +=
            `\n\n--- Slide ${i + 1} ---\n\n`;


        texto +=
            textoSlide.trim();

    }


    return texto.trim();

}


// =====================================
// MOSTRAR RESULTADO
// =====================================

function mostrarResultado() {

    if (!resultado) {
        return;
    }


    resultado.style.display =
        "block";


    if (nomeResultado) {

        nomeResultado.textContent =
            arquivoAtual.name;

    }


    const extensao =
        arquivoAtual.name
            .split(".")
            .pop()
            .toUpperCase();


    if (formatoResultado) {

        formatoResultado.textContent =
            extensao;

    }


    const idioma =
        document.getElementById(
            "idiomaDestino"
        );


    if (idioma && idiomaResultado) {

        idiomaResultado.textContent =
            idioma.options[
                idioma.selectedIndex
            ].text;

    }


    const modoSelecionado =
        document.querySelector(
            'input[name="modo"]:checked'
        );


    if (modoResultado) {

        const opcaoSelecionada =
            modoSelecionado?.closest(".opcao");

        const textoModo =
            opcaoSelecionada
                ?.querySelector("strong")
                ?.textContent
                ?.trim() ||
            modoSelecionado?.value ||
            "Tradução completa";

        modoResultado.textContent =
            textoModo;

    }


    // =================================
    // PREPARAR SLIDES
    // =================================

    prepararSlides();


    // =================================
    // MOSTRAR TEXTO NA VISUALIZAÇÃO
    // =================================

    if (
        visualizacao &&
        (!slideTitulo || !slideConteudo)
    ) {

        visualizacao.textContent =
            textoTraduzido;

    }


    resultado.scrollIntoView({
        behavior: "smooth"
    });

}


// =====================================
// PREPARAR SLIDES
// =====================================

function prepararSlides() {

    const extensao =
        arquivoAtual.name
            .split(".")
            .pop()
            .toLowerCase();


    slides = [];


    // =====================================
    // POWERPOINT
    // =====================================

    if (extensao === "pptx") {

        const partes =
            textoTraduzido
                .split(
                    /---\s*(?:\*?\s*)Slide\s+\d+\s*(?:\*?\s*)---/i
                )
                .map(
                    parte =>
                        parte.trim()
                )
                .filter(
                    parte =>
                        parte.length > 0
                );


        partes.forEach(
            (conteudo, indice) => {

                const linhas =
                    conteudo
                        .split(/\r?\n/)
                        .map(
                            linha =>
                                linha.trim()
                        )
                        .filter(
                            linha =>
                                linha.length > 0
                        );


                const titulo =
                    linhas.length > 0
                        ? linhas[0]
                        : `Slide ${indice + 1}`;


                const corpo =
                    linhas
                        .slice(1)
                        .join("\n");


                slides.push({

                    titulo:
                        titulo,

                    conteudo:
                        corpo

                });

            }
        );

    }


    // =====================================
    // PDF
    // =====================================

    else if (extensao === "pdf") {

        const partes =
            textoTraduzido
                .split(
                    /---\s*(?:\*?\s*)Página\s+\d+\s*(?:\*?\s*)---/i
                )
                .map(
                    parte =>
                        parte.trim()
                )
                .filter(
                    parte =>
                        parte.length > 0
                );


        partes.forEach(
            (conteudo, indice) => {

                slides.push({

                    titulo:
                        `Página ${indice + 1}`,

                    conteudo:
                        conteudo

                });

            }
        );

    }


    // =====================================
    // WORD
    // =====================================

    else {

        const tamanho =
            1200;


        for (
            let i = 0;
            i < textoTraduzido.length;
            i += tamanho
        ) {

            slides.push({

                titulo:
                    `Parte ${slides.length + 1}`,

                conteudo:
                    textoTraduzido
                        .substring(
                            i,
                            i + tamanho
                        )
                        .trim()

            });

        }

    }


    // =====================================
    // GARANTIR PELO MENOS UM SLIDE
    // =====================================

    if (slides.length === 0) {

        slides.push({

            titulo:
                "Material traduzido",

            conteudo:
                textoTraduzido

        });

    }


    slideAtual = 0;


    mostrarSlide();

}


// =====================================
// MOSTRAR SLIDE
// =====================================

function mostrarSlide() {

    if (!slides.length) {
        return;
    }


    const slide =
        slides[slideAtual];


    // =================================
    // SE EXISTIREM ELEMENTOS DE SLIDE
    // =================================

    if (slideNumero) {

        slideNumero.textContent =
            `Slide ${slideAtual + 1}`;

    }


    if (slideTitulo) {

        slideTitulo.textContent =
            slide.titulo;

    }


    if (slideConteudo) {

        slideConteudo.textContent =
            slide.conteudo;

    }


    if (contadorSlide) {

        contadorSlide.textContent =
            `${slideAtual + 1} / ${slides.length}`;

    }


    // =================================
    // SE O HTML SÓ TEM VISUALIZAÇÃO
    // =================================

    if (
        visualizacao &&
        !slideTitulo &&
        !slideConteudo
    ) {

        visualizacao.textContent =
            textoTraduzido;

    }


    atualizarBotoesSlides();

}


// =====================================
// ATUALIZAR BOTÕES DOS SLIDES
// =====================================

function atualizarBotoesSlides() {

    if (slideAnterior) {

        slideAnterior.disabled =
            slideAtual === 0;

    }


    if (slideProximo) {

        slideProximo.disabled =
            slideAtual === slides.length - 1;

    }

}


// =====================================
// SLIDE ANTERIOR
// =====================================

if (slideAnterior) {

    slideAnterior.addEventListener(
        "click",
        function () {

            if (slideAtual > 0) {

                slideAtual--;

                mostrarSlide();

            }

        }
    );

}


// =====================================
// PRÓXIMO SLIDE
// =====================================

if (slideProximo) {

    slideProximo.addEventListener(
        "click",
        function () {

            if (
                slideAtual <
                slides.length - 1
            ) {

                slideAtual++;

                mostrarSlide();

            }

        }
    );

}


// =====================================
// MENSAGENS
// =====================================

function mostrarMensagem(
    texto,
    erro = false
) {

    if (!mensagem) {
        return;
    }


    mensagem.textContent =
        texto;


    mensagem.style.color =
        erro
            ? "#b85c67"
            : "#7189a6";

}


// =====================================
// NOVO ARQUIVO
// =====================================

if (btnNovo) {

    btnNovo.addEventListener(
        "click",
        function () {

            if (arquivoInput) {

                arquivoInput.value =
                    "";

            }


            arquivoAtual =
                null;


            textoExtraido =
                "";


            textoTraduzido =
                "";


            slides =
                [];


            slideAtual =
                0;


            if (arquivoSelecionado) {

                arquivoSelecionado.textContent =
                    getTextoInterface(idiomaAtivo, "empty.file");

            }

            const uploadArea =
                document.querySelector(".upload-area");

            if (uploadArea) {
                uploadArea.classList.remove("is-filled");
            }


            if (slideNumero) {

                slideNumero.textContent =
                    "Slide 1";

            }


            if (slideTitulo) {

                slideTitulo.textContent =
                    "Tradução";

            }


            if (slideConteudo) {

                slideConteudo.textContent =
                    "O conteúdo traduzido aparecerá aqui.";

            }


            if (contadorSlide) {

                contadorSlide.textContent =
                    "1 / 1";

            }


            if (visualizacao) {

                visualizacao.textContent =
                    "O conteúdo do arquivo aparecerá aqui.";

            }


            if (resultado) {

                resultado.style.display =
                    "none";

            }


            if (mensagem) {

                mensagem.textContent =
                    "";

            }


            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });

        }
    );

}


// =====================================
// BAIXAR TRADUÇÃO
// =====================================

if (btnBaixar) {

    btnBaixar.addEventListener(
        "click",
        function () {

            if (!textoTraduzido) {

                mostrarMensagem(
                    "⚠️ Não existe conteúdo para baixar.",
                    true
                );

                return;

            }


            const blob =
                new Blob(
                    [textoTraduzido],
                    {
                        type:
                            "text/plain;charset=utf-8"
                    }
                );


            const url =
                URL.createObjectURL(
                    blob
                );


            const link =
                document.createElement(
                    "a"
                );


            link.href =
                url;


            link.download =
                "material-traduzido.txt";


            document.body.appendChild(
                link
            );


            link.click();


            document.body.removeChild(
                link
            );


            URL.revokeObjectURL(
                url
            );


            mostrarMensagem(
                "✅ Tradução baixada com sucesso!"
            );

        }
    );

}


// =====================================
// FUNÇÃO DE SEGURANÇA
// =====================================

function escaparHTML(texto) {

    const div =
        document.createElement("div");

    div.textContent =
        texto;

    return div.innerHTML;

}
