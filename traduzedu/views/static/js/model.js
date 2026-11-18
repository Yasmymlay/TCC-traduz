// =====================================
// MODEL (frontend)
// Estado da tela e comunicação com a API Flask.
// =====================================

const TraduzEduModel = (() => {
    const TAMANHO_MAXIMO_ARQUIVO = 10 * 1024 * 1024;
    const EXTENSOES_PERMITIDAS = new Set(["pdf"]);
    const IDIOMAS = {
        pt: "Português",
        en: "Inglês",
        es: "Espanhol"
    };
    const NOMES_PROVEDORES = {
        libretranslate: "LibreTranslate",
        argos: "Argos local",
        deepl: "DeepL"
    };

    const estado = {
        arquivoAtual: null,
        resultadoAtual: null,
        pdfTraduzidoUrl: null,
        slides: [],
        slideAtual: 0,
        requisicaoTraducao: null,
        tempoMaximoTraducaoSegundos: 300
    };

    async function lerJson(response) {
        return response.json().catch(() => ({}));
    }

    async function requisitarJson(url, opcoes = {}, mensagemPadrao = "Erro de comunicação.") {
        const response = await fetch(url, opcoes);
        const payload = await lerJson(response);
        if (!response.ok) {
            throw new Error(payload.error || mensagemPadrao);
        }
        return payload;
    }

    function postJson(url, corpo, mensagemPadrao) {
        return requisitarJson(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(corpo)
        }, mensagemPadrao);
    }

    // ---------- Regras de validação ----------

    function validarArquivo(arquivo) {
        const extensao = arquivo.name.split(".").pop().toLowerCase();
        if (!EXTENSOES_PERMITIDAS.has(extensao)) {
            return "Formato inválido. Selecione somente um arquivo PDF.";
        }
        if (!arquivo.size) {
            return "O arquivo está vazio. Selecione um documento com conteúdo.";
        }
        if (arquivo.size > TAMANHO_MAXIMO_ARQUIVO) {
            return "O arquivo excede o limite de 10 MB.";
        }
        return null;
    }

    function nomeIdioma(codigo) {
        return IDIOMAS[codigo] || codigo;
    }

    // ---------- Estado do resultado ----------

    function definirResultado(payload, { nomeArquivo, origem, destino }) {
        const paginas = Array.isArray(payload?.pages) ? payload.pages : [];
        const formato = (nomeArquivo || "arquivo").split(".").pop().toUpperCase();
        estado.resultadoAtual = {
            filename: nomeArquivo || "material",
            pages: paginas
        };
        estado.pdfTraduzidoUrl = payload?.translated_pdf_url || null;
        estado.slides = paginas.map((pagina) => ({
            ...pagina,
            formato,
            source_lang: payload?.source_lang || origem,
            target_lang: payload?.target_lang || destino
        }));
        estado.slideAtual = 0;
    }

    function limparResultado() {
        estado.slides = [];
        estado.resultadoAtual = null;
        estado.pdfTraduzidoUrl = null;
        estado.slideAtual = 0;
    }

    function irParaSlide(deslocamento) {
        if (!estado.slides.length) return false;
        const proximo = estado.slideAtual + deslocamento;
        estado.slideAtual = Math.min(estado.slides.length - 1, Math.max(0, proximo));
        return true;
    }

    // ---------- API ----------

    async function buscarStatusMecanismos() {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
            const payload = await requisitarJson(
                "/api/translation/status",
                { signal: controller.signal },
                "Não foi possível verificar os tradutores."
            );
            if (Number.isFinite(payload.max_translation_seconds)) {
                estado.tempoMaximoTraducaoSegundos = payload.max_translation_seconds;
            }
            const provedores = payload.providers || [];
            const nomes = (status) => provedores
                .filter((provider) => provider.status === status)
                .map((provider) => NOMES_PROVEDORES[provider.name] || provider.name);
            return { ativos: nomes("available"), configurados: nomes("configured") };
        } finally {
            clearTimeout(timeout);
        }
    }

    async function buscarStatusOCR(origem) {
        const response = await fetch(`/api/ocr/status?source_lang=${encodeURIComponent(origem)}`);
        const payload = await lerJson(response);
        return { ok: response.ok, ...payload };
    }

    function buscarModelosArgos(par) {
        const query = new URLSearchParams(par);
        return requisitarJson(`/api/argos/models?${query}`, {}, "Não foi possível verificar os modelos Argos.");
    }

    function consultarCatalogoArgos(par) {
        return postJson("/api/argos/catalog", par, "Não foi possível consultar o catálogo Argos.");
    }

    function instalarModeloArgos(par) {
        return postJson("/api/argos/models/install", par, "Não foi possível instalar o modelo Argos.");
    }

    function buscarDemonstracao(formato) {
        return requisitarJson(
            `/api/demo/${encodeURIComponent(formato)}`,
            {},
            "A demonstração não está disponível."
        );
    }

    async function traduzir(arquivo, origem, destino) {
        estado.requisicaoTraducao = new AbortController();
        const timeout = setTimeout(
            () => estado.requisicaoTraducao?.abort(),
            (estado.tempoMaximoTraducaoSegundos + 5) * 1000
        );
        try {
            const formData = new FormData();
            formData.append("file", arquivo);
            formData.append("source_lang", origem);
            formData.append("target_lang", destino);
            const payload = await requisitarJson("/api/translate", {
                method: "POST",
                body: formData,
                signal: estado.requisicaoTraducao.signal
            }, "Não foi possível concluir a tradução.");
            if (!payload.pages || !payload.pages.length) {
                throw new Error("Nenhuma página foi gerada na tradução.");
            }
            return payload;
        } finally {
            clearTimeout(timeout);
            estado.requisicaoTraducao = null;
        }
    }

    async function gerarDownload(formato) {
        // "pdf-layout": o próprio PDF enviado, com o texto traduzido no mesmo lugar.
        const mesmoLayout = formato === "pdf-layout";
        if (mesmoLayout && !estado.pdfTraduzidoUrl) {
            throw new Error("O PDF com o mesmo layout não está disponível para este resultado. Escolha outro formato.");
        }
        const response = mesmoLayout
            ? await fetch(estado.pdfTraduzidoUrl)
            : await fetch(`/api/download/${encodeURIComponent(formato)}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(estado.resultadoAtual)
            });
        if (!response.ok) {
            const payload = await lerJson(response);
            throw new Error(payload.error || "Não foi possível gerar o arquivo.");
        }
        const blob = await response.blob();
        if (!blob.size) throw new Error("O arquivo gerado está vazio.");
        const nomeBase = (estado.resultadoAtual.filename || "material")
            .replace(/\.[^.]+$/, "")
            .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_");
        const extensao = mesmoLayout ? "pdf" : formato;
        return { blob, nome: `${nomeBase || "material"}-traduzido.${extensao}`, extensao };
    }

    return {
        estado,
        validarArquivo,
        nomeIdioma,
        definirResultado,
        limparResultado,
        irParaSlide,
        buscarStatusMecanismos,
        buscarStatusOCR,
        buscarModelosArgos,
        consultarCatalogoArgos,
        instalarModeloArgos,
        buscarDemonstracao,
        traduzir,
        gerarDownload
    };
})();
