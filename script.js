// =====================================
// ELEMENTOS DO SITE
// =====================================

const arquivoInput =
    document.getElementById("arquivo");

const arquivoSelecionado =
    document.getElementById("arquivoSelecionado");

const btnTraduzir =
    document.getElementById("btnTraduzir");

const resultado =
    document.getElementById("resultado");

const mensagem =
    document.getElementById("mensagem");

const nomeResultado =
    document.getElementById("nomeResultado");

const formatoResultado =
    document.getElementById("formatoResultado");

const idiomaResultado =
    document.getElementById("idiomaResultado");

const modoResultado =
    document.getElementById("modoResultado");

const btnBaixar =
    document.getElementById("btnBaixar");

const btnNovo =
    document.getElementById("btnNovo");


// =====================================
// ELEMENTOS DOS SLIDES
// =====================================

const slideNumero =
    document.getElementById("slideNumero");

const slideTitulo =
    document.getElementById("slideTitulo");

const slideConteudo =
    document.getElementById("slideConteudo");

const contadorSlide =
    document.getElementById("contadorSlide");

const slideAnterior =
    document.getElementById("slideAnterior");

const slideProximo =
    document.getElementById("slideProximo");


// =====================================
// VARIÁVEIS
// =====================================

let arquivoAtual = null;

let textoExtraido = "";

let textoTraduzido = "";

let slides = [];

let slideAtual = 0;


// =====================================
// IDIOMAS DO CABEÇALHO
// =====================================

const botoesIdioma =
    document.querySelectorAll(
        ".idioma-selector button"
    );


botoesIdioma.forEach(botao => {

    botao.addEventListener("click", () => {

        botoesIdioma.forEach(b => {
            b.classList.remove("active");
        });

        botao.classList.add("active");

        console.log(
            "Idioma da interface:",
            botao.dataset.lang
        );

    });

});


// =====================================
// SELEÇÃO DO ARQUIVO
// =====================================

arquivoInput.addEventListener(
    "change",
    function () {

        arquivoAtual = this.files[0];

        if (!arquivoAtual) {

            arquivoSelecionado.textContent =
                "Nenhum arquivo selecionado.";

            return;
        }

        const extensao =
            arquivoAtual.name
                .split(".")
                .pop()
                .toLowerCase();

        const formatosPermitidos = [
            "pdf",
            "docx",
            "pptx"
        ];

        if (
            !formatosPermitidos.includes(
                extensao
            )
        ) {

            arquivoSelecionado.textContent =
                "❌ Formato não permitido.";

            arquivoAtual = null;

            return;
        }

        arquivoSelecionado.innerHTML =
            `📄 <strong>${arquivoAtual.name}</strong>`;

    }
);


// =====================================
// BOTÃO TRADUZIR
// =====================================

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


        const origem =
            document.getElementById(
                "idiomaOrigem"
            ).value;


        const destino =
            document.getElementById(
                "idiomaDestino"
            ).value;


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
                    await lerPDF(
                        arquivoAtual
                    );

            }

            else if (extensao === "docx") {

                textoExtraido =
                    await lerWord(
                        arquivoAtual
                    );

            }

            else if (extensao === "pptx") {

                textoExtraido =
                    await lerPowerPoint(
                        arquivoAtual
                    );

            }


            if (!textoExtraido) {

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


            if (!textoTraduzido) {

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

            btnTraduzir.disabled =
                false;

            btnTraduzir.textContent =
                "🔄 Preparar tradução";

        }

    }
);


// =====================================
// TRADUÇÃO COM LIBRETRANSLATE
// =====================================

async function traduzirTexto(
    texto,
    origem,
    destino
) {

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

        blocos =
            texto
                .split(
                    /(?=---\s*Slide\s+\d+\s*---)/i
                )
                .filter(
                    bloco =>
                        bloco.trim()
                            .length > 0
                );

    }


    // =====================================
    // PDF
    // =====================================

    else if (extensao === "pdf") {

        blocos =
            texto
                .split(
                    /(?=---\s*Página\s+\d+\s*---)/i
                )
                .filter(
                    bloco =>
                        bloco.trim()
                            .length > 0
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
                    /^---\s*(Slide|Página)\s+\d+\s*---/i
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


        mostrarMensagem(
            `🌎 Traduzindo ${
                extensao === "pptx"
                    ? "slide"
                    : extensao === "pdf"
                        ? "página"
                        : "conteúdo"
            } ${i + 1} de ${blocos.length}...`
        );


        // =================================
        // DIVIDIR TEXTO GRANDE
        // =================================

        const tamanhoMaximo =
            3000;


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
                            dados.toString()
                    }
                );


            if (!resposta.ok) {

                throw new Error(
                    "Erro ao conectar com o LibreTranslate."
                );

            }


            const resultadoAPI =
                await resposta.json();


            if (
                resultadoAPI.error
            ) {

                throw new Error(
                    resultadoAPI.error
                );

            }


            if (
                !resultadoAPI.translatedText
            ) {

                throw new Error(
                    "O LibreTranslate não retornou a tradução."
                );

            }


            partesTraduzidas.push(
                resultadoAPI.translatedText
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

    resultado.style.display =
        "block";


    nomeResultado.textContent =
        arquivoAtual.name;


    const extensao =
        arquivoAtual.name
            .split(".")
            .pop()
            .toUpperCase();


    formatoResultado.textContent =
        extensao;


    const idioma =
        document.getElementById(
            "idiomaDestino"
        );


    idiomaResultado.textContent =
        idioma.options[
            idioma.selectedIndex
        ].text;


    const modo =
        document.getElementById(
            "tipoTraducao"
        );


    modoResultado.textContent =
        modo.options[
            modo.selectedIndex
        ].text;


    // =================================
    // PREPARAR SLIDES
    // =================================

    prepararSlides();


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
                    /---\s*Slide\s+\d+\s*---/i
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
                    /---\s*Página\s+\d+\s*---/i
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
                    textoTraduzido.substring(
                        i,
                        i + tamanho
                    ).trim()

            });

        }

    }


    // =====================================
    // GARANTIR PELO MENOS UM SLIDE
    // =====================================

    if (
        slides.length === 0
    ) {

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


    slideNumero.textContent =
        `Slide ${slideAtual + 1}`;


    slideTitulo.textContent =
        slide.titulo;


    slideConteudo.textContent =
        slide.conteudo;


    contadorSlide.textContent =
        `${slideAtual + 1} / ${slides.length}`;


    atualizarBotoesSlides();

}


// =====================================
// ATUALIZAR BOTÕES DOS SLIDES
// =====================================

function atualizarBotoesSlides() {

    slideAnterior.disabled =
        slideAtual === 0;


    slideProximo.disabled =
        slideAtual ===
        slides.length - 1;

}


// =====================================
// SLIDE ANTERIOR
// =====================================

slideAnterior.addEventListener(
    "click",
    function () {

        if (slideAtual > 0) {

            slideAtual--;

            mostrarSlide();

        }

    }
);


// =====================================
// PRÓXIMO SLIDE
// =====================================

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


// =====================================
// MENSAGENS
// =====================================

function mostrarMensagem(
    texto,
    erro = false
) {

    mensagem.textContent =
        texto;


    mensagem.style.color =
        erro
            ? "#c62828"
            : "#2980b9";

}


// =====================================
// NOVO ARQUIVO
// =====================================

btnNovo.addEventListener(
    "click",
    function () {

        arquivoInput.value =
            "";

        arquivoAtual =
            null;

        textoExtraido =
            "";

        textoTraduzido =
            "";

        slides = [];

        slideAtual = 0;


        arquivoSelecionado.textContent =
            "Nenhum arquivo selecionado.";


        slideNumero.textContent =
            "Slide 1";


        slideTitulo.textContent =
            "Tradução";


        slideConteudo.textContent =
            "O conteúdo traduzido aparecerá aqui.";


        contadorSlide.textContent =
            "1 / 1";


        resultado.style.display =
            "none";


        mensagem.textContent =
            "";


        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }
);


// =====================================
// BAIXAR TRADUÇÃO
// =====================================

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

    }
);