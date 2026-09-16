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
// BOTÃO PREPARAR TRADUÇÃO
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


        mostrarMensagem(
            "⏳ Lendo o arquivo..."
        );


        btnTraduzir.disabled = true;


        try {

            const extensao =
                arquivoAtual.name
                    .split(".")
                    .pop()
                    .toLowerCase();


            // PDF

            if (extensao === "pdf") {

                textoExtraido =
                    await lerPDF(
                        arquivoAtual
                    );
            }


            // WORD

            else if (extensao === "docx") {

                textoExtraido =
                    await lerWord(
                        arquivoAtual
                    );
            }


            // POWERPOINT

            else if (extensao === "pptx") {

                textoExtraido =
                    await lerPowerPoint(
                        arquivoAtual
                    );
            }


            if (!textoExtraido) {

                throw new Error(
                    "Não foi possível encontrar texto no arquivo."
                );

            }


            mostrarResultado();


            mostrarMensagem(
                "✅ Arquivo lido com sucesso!"
            );

        }

        catch (erro) {

            console.error(erro);

            mostrarMensagem(
                "❌ Não foi possível ler o arquivo.",
                true
            );

        }

        finally {

            btnTraduzir.disabled = false;

        }

    }
);


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

    const btnTraduzir =
        document.getElementById("btnTraduzir");

    if (btnTraduzir) {
        btnTraduzir.textContent =
            t.preparar;
    }


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


    const botaoAtivo =
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


    visualizacao.textContent =
        textoExtraido;


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


/* =====================================================
   BOTÃO PT
===================================================== */

const btnPT =
    document.getElementById("btn-pt");

if (btnPT) {

    btnPT.addEventListener(
        "click",
        function () {

        arquivoInput.value =
            "";

        arquivoAtual =
            null;

        textoExtraido =
            "";

        arquivoSelecionado.textContent =
            "Nenhum arquivo selecionado.";

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
// BAIXAR TEXTO
// =====================================

btnBaixar.addEventListener(
    "click",
    function () {

        if (!textoExtraido) {

            mostrarMensagem(
                "⚠️ Não existe conteúdo para baixar.",
                true
            );

            return;
        }


        const blob =
            new Blob(
                [textoExtraido],
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
