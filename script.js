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

const visualizacao =
    document.getElementById("visualizacao");

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
// VARIÁVEIS
// =====================================

let arquivoAtual = null;

let textoExtraido = "";

let textoTraduzido = "";


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

        const idioma =
            botao.dataset.lang;

        console.log(
            "Idioma da interface:",
            idioma
        );

    });

});


// =====================================
// SELEÇÃO DO ARQUIVO
// =====================================

arquivoInput.addEventListener(
    "change",
    function () {

        arquivoAtual =
            this.files[0];

        textoExtraido = "";
        textoTraduzido = "";


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


        // Verificação do tamanho máximo de 10 MB

        if (
            arquivoAtual.size >
            10 * 1024 * 1024
        ) {

            arquivoSelecionado.textContent =
                "❌ O arquivo ultrapassa o limite de 10 MB.";

            arquivoAtual = null;

            return;
        }


        arquivoSelecionado.innerHTML =
            `📄 <strong>${arquivoAtual.name}</strong>`;

        mostrarMensagem(
            "✅ Arquivo selecionado. Clique em Traduzir agora."
        );

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


        btnTraduzir.disabled = true;

        btnTraduzir.textContent =
            "⏳ Lendo arquivo...";


        try {

            const extensao =
                arquivoAtual.name
                    .split(".")
                    .pop()
                    .toLowerCase();


            // =================================
            // PDF
            // =================================

            if (extensao === "pdf") {

                textoExtraido =
                    await lerPDF(
                        arquivoAtual
                    );

            }


            // =================================
            // WORD
            // =================================

            else if (extensao === "docx") {

                textoExtraido =
                    await lerWord(
                        arquivoAtual
                    );

            }


            // =================================
            // POWERPOINT
            // =================================

            else if (extensao === "pptx") {

                textoExtraido =
                    await lerPowerPoint(
                        arquivoAtual
                    );

            }


            if (
                !textoExtraido ||
                !textoExtraido.trim()
            ) {

                throw new Error(
                    "Não foi possível encontrar texto no arquivo."
                );

            }


            // =================================
            // IDIOMAS
            // =================================

            const origem =
                document.getElementById(
                    "idiomaOrigem"
                ).value;


            const destino =
                document.getElementById(
                    "idiomaDestino"
                ).value;


            // =================================
            // TRADUÇÃO
            // =================================

            btnTraduzir.textContent =
                "🌎 Traduzindo...";


            mostrarMensagem(
                "🌎 Enviando conteúdo para tradução..."
            );


            textoTraduzido =
                await traduzirTexto(
                    textoExtraido,
                    origem,
                    destino
                );


            // =================================
            // MOSTRAR RESULTADO
            // =================================

            mostrarResultado();


            mostrarMensagem(
                "✅ Tradução concluída com sucesso!"
            );

        }


        catch (erro) {

            console.error(
                "Erro:",
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
                "<span>⟳</span> Traduzir agora";

        }

    }
);


// =====================================
// TRADUZIR TEXTO COM LIBRETRANSLATE
// =====================================

async function traduzirTexto(
    texto,
    origem,
    destino
) {

    // Se os idiomas forem iguais,
    // não precisamos chamar a API.

    if (origem === destino) {

        return texto;

    }


    /*
        O LibreTranslate funciona melhor
        quando enviamos o texto usando
        application/x-www-form-urlencoded.

        Isso também evita o problema de JSON
        que tivemos no teste do PowerShell.
    */


    const tamanhoMaximo = 4000;


    const partes = [];


    for (
        let i = 0;
        i < texto.length;
        i += tamanhoMaximo
    ) {

        partes.push(
            texto.substring(
                i,
                i + tamanhoMaximo
            )
        );

    }


    const traducoes = [];


    for (
        let i = 0;
        i < partes.length;
        i++
    ) {

        mostrarMensagem(
            `🌎 Traduzindo parte ${i + 1} de ${partes.length}...`
        );


        const dados =
            new URLSearchParams();


        dados.append(
            "q",
            partes[i]
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

                    body: dados.toString()

                }
            );


        if (!resposta.ok) {

            throw new Error(
                "O LibreTranslate não conseguiu realizar a tradução."
            );

        }


        const dadosResposta =
            await resposta.json();


        if (
            !dadosResposta.translatedText
        ) {

            throw new Error(
                "A API não retornou o texto traduzido."
            );

        }


        traducoes.push(
            dadosResposta.translatedText
        );

    }


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
            await pdf.getPage(pagina);


        const content =
            await page.getTextContent();


        const linhas =
            content.items
                .map(item => item.str)
                .join(" ");


        texto +=
            `\n\n--- Página ${pagina} ---\n\n`;


        texto += linhas;

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
        Object.keys(zip.files);


    const slides =
        arquivos
            .filter(nome =>
                /^ppt\/slides\/slide\d+\.xml$/
                    .test(nome)
            )
            .sort((a, b) => {

                const numeroA =
                    parseInt(
                        a.match(/slide(\d+)/)[1]
                    );


                const numeroB =
                    parseInt(
                        b.match(/slide(\d+)/)[1]
                    );


                return numeroA - numeroB;

            });


    for (
        let i = 0;
        i < slides.length;
        i++
    ) {

        const nomeSlide =
            slides[i];


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


    // IMPORTANTE:
    // Agora mostramos a tradução,
    // e não mais o texto original.

    visualizacao.textContent =
        textoTraduzido;


    resultado.scrollIntoView({
        behavior: "smooth"
    });

}


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


        arquivoSelecionado.textContent =
            "Nenhum arquivo selecionado";


        visualizacao.textContent =
            "O conteúdo do arquivo aparecerá aqui.";


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
                "⚠️ Não existe tradução para baixar.",
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
            URL.createObjectURL(blob);


        const link =
            document.createElement("a");


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