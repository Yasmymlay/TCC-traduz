/* =====================================================
   TRADUÇÃO DO SITE
   PT = Português
   ES = Espanhol
   EN = Inglês

   Não precisa alterar o HTML.
===================================================== */


/* =====================================================
   TEXTOS DOS IDIOMAS
===================================================== */

const textos = {

    pt: {

        logo: "🎓 Tradutor de Aulas",

        bannerTitulo: "📚 Tradutor de Aulas",

        bannerDescricao:
            "Traduza seus materiais de estudo de forma simples e rápida.",

        enviarMaterial:
            "📄 Envie seu material",

        formatos:
            "PDF • Word • PowerPoint",

        escolherArquivo:
            "Escolher arquivo",

        tiposArquivo:
            "PDF, Word ou PowerPoint",

        nenhumArquivo:
            "Nenhum arquivo selecionado.",

        idiomaOrigem:
            "🇧🇷 Idioma original",

        idiomaDestino:
            "🇪🇸 Traduzir para",

        tipoTraducao:
            "🎓 Tipo de tradução",

        traducaoAcademica:
            "🎓 Tradução acadêmica/pedagógica",

        traducaoComum:
            "🌎 Tradução comum",

        preparar:
            "🔄 Preparar tradução",

        materialCarregado:
            "✅ Material carregado",

        arquivo:
            "Arquivo:",

        formato:
            "Formato:",

        idiomaResultado:
            "Idioma destino:",

        modo:
            "Modo:",

        visualizacao:
            "👁 Visualização do conteúdo",

        conteudo:
            "O conteúdo do arquivo aparecerá aqui.",

        baixar:
            "⬇ Baixar conteúdo",

        novoArquivo:
            "📤 Novo arquivo",

        rodape:
            "Tradutor de Aulas • Projeto de TCC"

    },


    es: {

        logo: "🎓 Traductor de Clases",

        bannerTitulo:
            "📚 Traductor de Clases",

        bannerDescricao:
            "Traduce tus materiales de estudio de forma sencilla y rápida.",

        enviarMaterial:
            "📄 Envía tu material",

        formatos:
            "PDF • Word • PowerPoint",

        escolherArquivo:
            "Elegir archivo",

        tiposArquivo:
            "PDF, Word o PowerPoint",

        nenhumArquivo:
            "Ningún archivo seleccionado.",

        idiomaOrigem:
            "🇧🇷 Idioma original",

        idiomaDestino:
            "🇪🇸 Traducir a",

        tipoTraducao:
            "🎓 Tipo de traducción",

        traducaoAcademica:
            "🎓 Traducción académica/pedagógica",

        traducaoComum:
            "🌎 Traducción común",

        preparar:
            "🔄 Preparar traducción",

        materialCarregado:
            "✅ Material cargado",

        arquivo:
            "Archivo:",

        formato:
            "Formato:",

        idiomaResultado:
            "Idioma de destino:",

        modo:
            "Modo:",

        visualizacao:
            "👁 Visualización del contenido",

        conteudo:
            "El contenido del archivo aparecerá aquí.",

        baixar:
            "⬇ Descargar contenido",

        novoArquivo:
            "📤 Nuevo archivo",

        rodape:
            "Traductor de Clases • Proyecto de TCC"

    },


    en: {

        logo:
            "🎓 Lesson Translator",

        bannerTitulo:
            "📚 Lesson Translator",

        bannerDescricao:
            "Translate your study materials simply and quickly.",

        enviarMaterial:
            "📄 Upload your material",

        formatos:
            "PDF • Word • PowerPoint",

        escolherArquivo:
            "Choose file",

        tiposArquivo:
            "PDF, Word or PowerPoint",

        nenhumArquivo:
            "No file selected.",

        idiomaOrigem:
            "🇧🇷 Original language",

        idiomaDestino:
            "🇪🇸 Translate to",

        tipoTraducao:
            "🎓 Translation type",

        traducaoAcademica:
            "🎓 Academic/pedagogical translation",

        traducaoComum:
            "🌎 Common translation",

        preparar:
            "🔄 Prepare translation",

        materialCarregado:
            "✅ Material loaded",

        arquivo:
            "File:",

        formato:
            "Format:",

        idiomaResultado:
            "Target language:",

        modo:
            "Mode:",

        visualizacao:
            "👁 Content preview",

        conteudo:
            "The file content will appear here.",

        baixar:
            "⬇ Download content",

        novoArquivo:
            "📤 New file",

        rodape:
            "Lesson Translator • TCC Project"

    }

};


/* =====================================================
   FUNÇÃO PARA TROCAR O IDIOMA
===================================================== */

function mudarIdioma(idioma) {

    const t = textos[idioma];

    if (!t) {
        return;
    }


    /* ==============================
       LOGO
    ============================== */

    const logo = document.querySelector(".logo");

    if (logo) {
        logo.textContent = t.logo;
    }


    /* ==============================
       BANNER
    ============================== */

    const bannerTitulo =
        document.querySelector(".banner h1");

    if (bannerTitulo) {
        bannerTitulo.textContent =
            t.bannerTitulo;
    }


    const bannerDescricao =
        document.querySelector(".banner p");

    if (bannerDescricao) {
        bannerDescricao.textContent =
            t.bannerDescricao;
    }


    /* ==============================
       CARD
    ============================== */

    const cardTitulo =
        document.querySelector(".card h2");

    if (cardTitulo) {
        cardTitulo.textContent =
            t.enviarMaterial;
    }


    const subtitulo =
        document.querySelector(".subtitulo");

    if (subtitulo) {
        subtitulo.textContent =
            t.formatos;
    }


    /* ==============================
       UPLOAD
    ============================== */

    const uploadStrong =
        document.querySelector(".upload-area strong");

    if (uploadStrong) {
        uploadStrong.textContent =
            t.escolherArquivo;
    }


    const uploadSpan =
        document.querySelector(".upload-area span");

    if (uploadSpan) {
        uploadSpan.textContent =
            t.tiposArquivo;
    }


    /* ==============================
       ARQUIVO SELECIONADO
    ============================== */

    const arquivoSelecionado =
        document.getElementById(
            "arquivoSelecionado"
        );

    /*
       Só altera se ainda não houver
       um arquivo escolhido.
    */

    const inputArquivo =
        document.getElementById("arquivo");

    if (
        arquivoSelecionado &&
        inputArquivo &&
        inputArquivo.files.length === 0
    ) {

        arquivoSelecionado.textContent =
            t.nenhumArquivo;
    }


    /* ==============================
       IDIOMA DE ORIGEM
    ============================== */

    const labelOrigem =
        document.querySelector(
            'label[for="idiomaOrigem"]'
        );

    if (labelOrigem) {
        labelOrigem.textContent =
            t.idiomaOrigem;
    }


    /* ==============================
       IDIOMA DE DESTINO
    ============================== */

    const labelDestino =
        document.querySelector(
            'label[for="idiomaDestino"]'
        );

    if (labelDestino) {
        labelDestino.textContent =
            t.idiomaDestino;
    }


    /* ==============================
       TIPO DE TRADUÇÃO
    ============================== */

    const labelTipo =
        document.querySelector(
            'label[for="tipoTraducao"]'
        );

    if (labelTipo) {
        labelTipo.textContent =
            t.tipoTraducao;
    }


    /* ==============================
       OPÇÕES DO TIPO DE TRADUÇÃO
    ============================== */

    const selectTipo =
        document.getElementById("tipoTraducao");

    if (selectTipo) {

        const opcaoAcademica =
            selectTipo.querySelector(
                'option[value="academica"]'
            );

        const opcaoComum =
            selectTipo.querySelector(
                'option[value="comum"]'
            );

        if (opcaoAcademica) {
            opcaoAcademica.textContent =
                t.traducaoAcademica;
        }

        if (opcaoComum) {
            opcaoComum.textContent =
                t.traducaoComum;
        }
    }


    /* ==============================
       BOTÃO PRINCIPAL
    ============================== */

    const btnTraduzir =
        document.getElementById("btnTraduzir");

    if (btnTraduzir) {
        btnTraduzir.textContent =
            t.preparar;
    }


    /* ==============================
       RESULTADO
    ============================== */

    const resultadoTitulo =
        document.querySelector(
            ".resultado h2"
        );

    if (resultadoTitulo) {
        resultadoTitulo.textContent =
            t.materialCarregado;
    }


    /* ==============================
       INFORMAÇÕES
    ============================== */

    const informacoes =
        document.querySelectorAll(
            ".informacoes p"
        );

    if (informacoes.length >= 4) {

        informacoes[0].querySelector("strong").textContent =
            t.arquivo;

        informacoes[1].querySelector("strong").textContent =
            t.formato;

        informacoes[2].querySelector("strong").textContent =
            t.idiomaResultado;

        informacoes[3].querySelector("strong").textContent =
            t.modo;
    }


    /* ==============================
       VISUALIZAÇÃO
    ============================== */

    const visualizacaoTitulo =
        document.querySelector(
            ".card h3"
        );

    if (visualizacaoTitulo) {
        visualizacaoTitulo.textContent =
            t.visualizacao;
    }


    const visualizacao =
        document.getElementById(
            "visualizacao"
        );

    if (visualizacao) {
        visualizacao.textContent =
            t.conteudo;
    }


    /* ==============================
       BOTÕES DO RESULTADO
    ============================== */

    const btnBaixar =
        document.getElementById(
            "btnBaixar"
        );

    if (btnBaixar) {
        btnBaixar.textContent =
            t.baixar;
    }


    const btnNovo =
        document.getElementById(
            "btnNovo"
        );

    if (btnNovo) {
        btnNovo.textContent =
            t.novoArquivo;
    }


    /* ==============================
       RODAPÉ
    ============================== */

    const footer =
        document.querySelector("footer p");

    if (footer) {
        footer.textContent =
            t.rodape;
    }


    /* =================================================
       ATUALIZA OS BOTÕES PT / ES / EN
    ================================================= */

    document
        .querySelectorAll(".idioma-selector button")
        .forEach(function (botao) {

            botao.classList.remove("active");

        });


    const botaoAtivo =
        document.getElementById(
            "btn-" + idioma
        );

    if (botaoAtivo) {

        botaoAtivo.classList.add(
            "active"
        );

    }


    /* =================================================
       GUARDA O IDIOMA ESCOLHIDO
    ================================================= */

    localStorage.setItem(
        "idiomaSite",
        idioma
    );
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

            mudarIdioma("pt");

        }
    );
}


/* =====================================================
   BOTÃO ES
===================================================== */

const btnES =
    document.getElementById("btn-es");

if (btnES) {

    btnES.addEventListener(
        "click",
        function () {

            mudarIdioma("es");

        }
    );
}


/* =====================================================
   BOTÃO EN
===================================================== */

const btnEN =
    document.getElementById("btn-en");

if (btnEN) {

    btnEN.addEventListener(
        "click",
        function () {

            mudarIdioma("en");

        }
    );
}


/* =====================================================
   RECUPERA O IDIOMA SALVO
===================================================== */

const idiomaSalvo =
    localStorage.getItem(
        "idiomaSite"
    );


if (idiomaSalvo && textos[idiomaSalvo]) {

    mudarIdioma(idiomaSalvo);

} else {

    mudarIdioma("pt");

}