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
const btnAnterior = document.getElementById("btnAnterior");
const btnProximo = document.getElementById("btnProximo");
const contadorSlides = document.getElementById("contadorSlides");
const btnDemo = document.getElementById("btnDemo");
const demoFormato = document.getElementById("demoFormato");
const linkDemoArquivo = document.getElementById("linkDemoArquivo");
const seloDemo = document.getElementById("seloDemo");
const statusMecanismos = document.getElementById("statusMecanismos");
const statusOCR = document.getElementById("statusOCR");
const statusModelosArgos = document.getElementById("statusModelosArgos");
const btnVerificarCatalogo = document.getElementById("btnVerificarCatalogo");
const btnInstalarModelo = document.getElementById("btnInstalarModelo");
const formatoDownload = document.getElementById("formatoDownload");

// =====================================
// VARIÁVEIS
// =====================================

let arquivoAtual = null;
let resultadoAtual = null;
let slides = [];
let slideAtual = 0;
let requisicaoTraducao = null;
const arquivoAbertoDiretamente = window.location.protocol === "file:";
const avisoServidorLocal = "Para traduzir, feche esta página, execute iniciar.bat na pasta do projeto e use o endereço http://127.0.0.1:5001 que será aberto.";
const tamanhoMaximoArquivo = 10 * 1024 * 1024;
let tempoMaximoTraducaoSegundos = 300;
const extensoesPermitidas = new Set(["pdf"]);

const idiomaMap = {
    pt: "Português",
    en: "Inglês",
    es: "Espanhol"
};

function escapeHtml(value = "") {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function mostrarMensagem(texto, erro = false) {
    if (!mensagem) return;
    mensagem.textContent = texto;
    mensagem.classList.toggle("is-error", erro);
    mensagem.classList.toggle("is-success", !erro);
}

if (arquivoAbertoDiretamente) {
    mostrarMensagem(`⚠️ ${avisoServidorLocal}`, true);
}

function renderSlidePreview(index = 0) {
    if (!slides.length || !visualizacao) {
        if (visualizacao) {
            visualizacao.innerHTML = `
                <div class="resultado-vazio">
                    <span class="resultado-vazio-icone" aria-hidden="true">
                        <svg viewBox="0 0 52 52" fill="none"><rect x="7" y="7" width="38" height="38" rx="14" stroke="currentColor" stroke-width="1.6" /><path d="M17 20h18M17 26h18M17 32h11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
                    </span>
                    <strong>Seu resultado aparecerá aqui</strong>
                    <span>Envie um documento para visualizar o conteúdo traduzido.</span>
                </div>
            `;
        }
        if (contadorSlides) {
            contadorSlides.textContent = "1 / 1";
        }
        return;
    }

    const slide = slides[index] || slides[0];
    const pageTitle = slide.page_title || `Página ${index + 1}`;
    const documentTitle = slide.title || "Material traduzido";
    const subtitle = slide.subtitle || "";
    const blocks = slide.blocks || [];

    const itensHtml = blocks.map((block) => {
        const text = escapeHtml(block && block.text ? block.text : "");
        if (!text) return "";

        const type = block.type || "paragraph";
        if (type === "heading") {
            return `<h3 class="slide-heading">${text}</h3>`;
        }

        if (type === "list-item" || /^\d+[.)]\s/.test(text.trim())) {
            return `<p class="slide-list-item">${type === "list-item" ? "• " : ""}${text}</p>`;
        }

        if (type === "table-row") {
            return `<p class="slide-table-row">${text}</p>`;
        }

        return `<p class="slide-question">${text}</p>`;
    }).join("");

    visualizacao.innerHTML = `
        <div class="slide-preview">
            <header class="slide-header">
                <div class="logo-box">
                    <span class="logo-icone">🎓</span>
                    <span class="logo-texto">Tradutor de Aulas</span>
                </div>
                <p class="subtitulo">Seu material traduzido e organizado</p>
            </header>

            <main class="slide-content">
                <div class="slide-title-row">
                    <div class="slide-title-wrap">
                        <div class="slide-icon">📄</div>
                        <h1>${escapeHtml(documentTitle)}</h1>
                    </div>
                    <span class="slide-badge">Traduzido</span>
                </div>

                <div class="slide-meta">${escapeHtml((slide.formato || "PDF") + " • " + (slide.source_lang || "pt") + " → " + (slide.target_lang || "es"))}</div>
                <div class="slide-divider"></div>

                <section class="slide-body">
                    <h2>${escapeHtml(pageTitle)}</h2>
                    ${subtitle ? `<h3>${escapeHtml(subtitle)}</h3>` : ""}

                    <div class="slide-panel">
                        ${itensHtml || '<p class="slide-question">Esta página não possui texto legível.</p>'}
                    </div>
                </section>
            </main>
        </div>
    `;

    if (contadorSlides) {
        contadorSlides.textContent = `${index + 1} / ${slides.length}`;
    }

    if (btnAnterior) {
        btnAnterior.disabled = index === 0;
    }

    if (btnProximo) {
        btnProximo.disabled = index >= slides.length - 1;
    }
}

function atualizarResumoArquivo(fileName, origem, destino, modoTexto) {
    if (nomeResultado) {
        nomeResultado.textContent = fileName || "-";
    }

    if (formatoResultado) {
        const extensao = fileName ? fileName.split('.').pop().toUpperCase() : "-";
        formatoResultado.textContent = extensao === "-" ? "-" : extensao;
    }

    if (idiomaResultado) {
        idiomaResultado.textContent = `${idiomaMap[origem] || origem} → ${idiomaMap[destino] || destino}`;
    }

    if (modoResultado) {
        modoResultado.textContent = modoTexto || "Tradução completa";
    }
}

function montarResultado(payload) {
    const arquivo = arquivoInput && arquivoInput.files[0];
    const origem = document.getElementById("idiomaOrigem")?.value || "pt";
    const destino = document.getElementById("idiomaDestino")?.value || "en";
    const modoSelecionado = document.querySelector('input[name="modo"]:checked');

    const modoTexto = payload?.demo
        ? "Demonstração preparada"
        : modoSelecionado
            ? modoSelecionado.parentElement.querySelector("strong").textContent
            : "Tradução completa";
    const idiomaOrigem = payload?.source_lang || origem;
    const idiomaDestino = payload?.target_lang || destino;
    atualizarResumoArquivo(
        arquivo ? arquivo.name : payload?.filename || "-",
        idiomaOrigem,
        idiomaDestino,
        modoTexto
    );
    if (seloDemo) seloDemo.hidden = !payload?.demo;
    resultadoAtual = {
        filename: arquivo ? arquivo.name : payload?.filename || "material",
        pages: Array.isArray(payload?.pages) ? payload.pages : []
    };

    slides = Array.isArray(payload?.pages) ? payload.pages.map((page) => ({
        ...page,
        formato: (arquivo ? arquivo.name : payload?.filename || "arquivo").split('.').pop().toUpperCase(),
        source_lang: payload?.source_lang || origem,
        target_lang: payload?.target_lang || destino,
    })) : [];

    slideAtual = 0;
    renderSlidePreview(slideAtual);
}

function atualizarArquivoDemo() {
    if (linkDemoArquivo && demoFormato) {
        linkDemoArquivo.href = `/tmp-docs/sample.${encodeURIComponent(demoFormato.value)}`;
    }
}

async function atualizarStatusMecanismos() {
    if (!statusMecanismos) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
        const response = await fetch("/api/translation/status", { signal: controller.signal });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.error || "Não foi possível verificar os tradutores.");
        }
        if (Number.isFinite(payload.max_translation_seconds)) {
            tempoMaximoTraducaoSegundos = payload.max_translation_seconds;
        }

        const nomes = {
            libretranslate: "LibreTranslate",
            argos: "Argos local",
            deepl: "DeepL"
        };
        const ativos = (payload.providers || [])
            .filter((provider) => provider.status === "available")
            .map((provider) => nomes[provider.name] || provider.name);
        const configurados = (payload.providers || [])
            .filter((provider) => provider.status === "configured")
            .map((provider) => nomes[provider.name] || provider.name);

        const detalhes = [];
        if (ativos.length) detalhes.push(`Disponíveis: ${ativos.join(", ")}.`);
        if (configurados.length) detalhes.push(`Configurados: ${configurados.join(", ")}.`);
        if (!detalhes.length) {
            detalhes.push("Tradutores indisponíveis. Você ainda pode usar a demonstração offline.");
            statusMecanismos.classList.add("is-error");
        } else {
            statusMecanismos.classList.remove("is-error");
        }
        statusMecanismos.textContent = detalhes.join(" ");
    } catch (erro) {
        statusMecanismos.textContent = erro.name === "AbortError"
            ? "A verificação dos tradutores demorou demais; você ainda pode tentar traduzir ou abrir a demonstração."
            : `Não foi possível verificar os tradutores: ${erro.message || "erro de comunicação"}`;
        statusMecanismos.classList.add("is-error");
    } finally {
        clearTimeout(timeout);
    }
}

function parIdiomasSelecionado() {
    return {
        source: document.getElementById("idiomaOrigem")?.value || "pt",
        target: document.getElementById("idiomaDestino")?.value || "en"
    };
}

async function atualizarStatusOCR() {
    if (!statusOCR) return;
    const source = parIdiomasSelecionado().source;
    try {
        const response = await fetch(`/api/ocr/status?source_lang=${encodeURIComponent(source)}`);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.available || payload.missing_languages?.length) {
            statusOCR.textContent = payload.error || "OCR indisponível neste computador.";
            statusOCR.classList.add("is-error");
            return;
        }
        statusOCR.textContent = `OCR disponível (${payload.version}; idiomas: ${payload.languages.join(", ")}). PDFs digitalizados serão reconhecidos automaticamente.`;
        statusOCR.classList.remove("is-error");
    } catch (erro) {
        statusOCR.textContent = `Não foi possível verificar o OCR: ${erro.message || "erro de comunicação"}`;
        statusOCR.classList.add("is-error");
    }
}

function mostrarStatusArgos(payload) {
    if (!statusModelosArgos) return;
    if (btnInstalarModelo) btnInstalarModelo.hidden = true;
    if (payload.installed) {
        statusModelosArgos.textContent = `O par ${payload.source} → ${payload.target} já está instalado e disponível localmente.`;
        return;
    }
    if (!payload.catalog_checked) {
        statusModelosArgos.textContent = `O par ${payload.source} → ${payload.target} não está instalado. Consulte o catálogo online para verificar se o modelo está disponível; nenhum modelo será baixado nessa consulta.`;
        return;
    }
    if (payload.package_available) {
        statusModelosArgos.textContent = `Modelo ${payload.source} → ${payload.target}, versão ${payload.package_version}, disponível em ${payload.download_host || "catálogo Argos"}. A instalação só começa depois de sua confirmação.`;
        if (btnInstalarModelo) {
            btnInstalarModelo.textContent = `Instalar ${payload.source} → ${payload.target}`;
            btnInstalarModelo.hidden = false;
        }
        return;
    }
    statusModelosArgos.textContent = `O catálogo consultado não oferece o modelo direto ${payload.source} → ${payload.target}. Nenhum modelo foi baixado.`;
}

async function atualizarStatusArgos() {
    if (!statusModelosArgos) return;
    const pair = parIdiomasSelecionado();
    statusModelosArgos.textContent = "Verificando modelos locais...";
    if (btnInstalarModelo) btnInstalarModelo.hidden = true;
    try {
        const query = new URLSearchParams(pair);
        const response = await fetch(`/api/argos/models?${query}`);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Não foi possível verificar os modelos Argos.");
        mostrarStatusArgos(payload);
    } catch (erro) {
        statusModelosArgos.textContent = erro.message || "Não foi possível verificar os modelos Argos.";
    }
}

async function consultarCatalogoArgos() {
    if (!btnVerificarCatalogo) return;
    const pair = parIdiomasSelecionado();
    btnVerificarCatalogo.disabled = true;
    btnVerificarCatalogo.textContent = "Consultando catálogo...";
    try {
        const response = await fetch("/api/argos/catalog", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(pair)
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Não foi possível consultar o catálogo Argos.");
        mostrarStatusArgos(payload);
        mostrarMensagem(
            "Catálogo Argos consultado. Essa verificação não baixa modelos de tradução."
        );
    } catch (erro) {
        mostrarMensagem(erro.message || "Não foi possível consultar o catálogo Argos.", true);
    } finally {
        btnVerificarCatalogo.disabled = false;
        btnVerificarCatalogo.textContent = "Consultar catálogo Argos";
    }
}

async function instalarModeloArgos() {
    if (!btnInstalarModelo) return;
    const pair = parIdiomasSelecionado();
    const confirmation = (
        `O modelo Argos ${pair.source} → ${pair.target} será baixado do catálogo verificado `
        + "e instalado neste computador. Deseja continuar?"
    );
    if (!window.confirm(confirmation)) return;

    btnInstalarModelo.disabled = true;
    btnInstalarModelo.textContent = "Baixando e instalando...";
    try {
        const response = await fetch("/api/argos/models/install", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(pair)
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Não foi possível instalar o modelo Argos.");
        mostrarStatusArgos(payload);
        mostrarMensagem(`Modelo Argos ${pair.source} → ${pair.target} instalado e verificado.`);
    } catch (erro) {
        mostrarMensagem(erro.message || "Não foi possível instalar o modelo Argos.", true);
    } finally {
        btnInstalarModelo.disabled = false;
    }
}

if (btnVerificarCatalogo) {
    btnVerificarCatalogo.addEventListener("click", consultarCatalogoArgos);
}
if (btnInstalarModelo) {
    btnInstalarModelo.addEventListener("click", instalarModeloArgos);
}
for (const id of ["idiomaOrigem", "idiomaDestino"]) {
    document.getElementById(id)?.addEventListener("change", () => {
        atualizarStatusArgos();
        atualizarStatusOCR();
    });
}

if (demoFormato) {
    demoFormato.addEventListener("change", atualizarArquivoDemo);
    atualizarArquivoDemo();
}

if (btnDemo) {
    btnDemo.addEventListener("click", async () => {
        const format = demoFormato?.value;
        if (!format) return;

        btnDemo.disabled = true;
        btnDemo.textContent = "Carregando exemplo...";
        try {
            const response = await fetch(`/api/demo/${encodeURIComponent(format)}`);
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.error || "A demonstração não está disponível.");
            }

            atualizarArquivo(null);
            const origemDemo = document.getElementById("idiomaOrigem");
            const destinoDemo = document.getElementById("idiomaDestino");
            if (origemDemo) origemDemo.value = payload.source_lang;
            if (destinoDemo) destinoDemo.value = payload.target_lang;
            montarResultado(payload);
            mostrarMensagem(
                "Modo demonstração: este resultado preparado não é uma tradução do seu arquivo."
            );
            if (resultado) {
                resultado.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        } catch (erro) {
            mostrarMensagem(`❌ ${erro.message || "Não foi possível carregar a demonstração."}`, true);
        } finally {
            btnDemo.disabled = false;
            btnDemo.textContent = "Carregar demonstração";
        }
    });
}

atualizarStatusMecanismos();
atualizarStatusArgos();
atualizarStatusOCR();

// =====================================
// SELEÇÃO DO ARQUIVO
// =====================================

function atualizarArquivo(file) {
    arquivoAtual = file || null;
    if (!arquivoInput) return;

    if (!arquivoAtual) {
        arquivoInput.value = "";
        if (arquivoSelecionado) {
            arquivoSelecionado.innerHTML = '<span class="arquivo-vazio-icone" aria-hidden="true">+</span><span>Nenhum arquivo selecionado</span>';
        }
        document.querySelector(".upload-area")?.classList.remove("is-filled");
        return;
    }

    const extensao = arquivoAtual.name.split(".").pop().toLowerCase();
    if (!extensoesPermitidas.has(extensao)) {
        mostrarMensagem("❌ Formato inválido. Selecione somente um arquivo PDF.", true);
        atualizarArquivo(null);
        return;
    }

    if (!arquivoAtual.size) {
        mostrarMensagem("❌ O arquivo está vazio. Selecione um documento com conteúdo.", true);
        atualizarArquivo(null);
        return;
    }

    if (arquivoAtual.size > tamanhoMaximoArquivo) {
        mostrarMensagem("❌ O arquivo excede o limite de 10 MB.", true);
        atualizarArquivo(null);
        return;
    }

    if (arquivoSelecionado) {
        arquivoSelecionado.innerHTML = `📄 <strong>${escapeHtml(arquivoAtual.name)}</strong>`;
    }
    document.querySelector(".upload-area")?.classList.add("is-filled");
    mostrarMensagem("✅ Arquivo selecionado.");
}

if (arquivoInput) {
    arquivoInput.addEventListener("change", () => atualizarArquivo(arquivoInput.files[0]));
}

const uploadArea = document.querySelector(".upload-area");
if (uploadArea) {
    ["dragenter", "dragover"].forEach((eventName) => {
        uploadArea.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadArea.classList.add("is-dragging");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        uploadArea.addEventListener(eventName, (event) => {
            event.preventDefault();
            uploadArea.classList.remove("is-dragging");
        });
    });

    uploadArea.addEventListener("drop", (event) => {
        const file = event.dataTransfer?.files[0];
        if (!file || !arquivoInput) return;

        const transfer = new DataTransfer();
        transfer.items.add(file);
        arquivoInput.files = transfer.files;
        atualizarArquivo(file);
    });
}

// =====================================
// BOTÃO TRADUZIR
// =====================================

if (btnTraduzir) {
    btnTraduzir.addEventListener("click", async function () {
        if (arquivoAbertoDiretamente) {
            mostrarMensagem(`⚠️ ${avisoServidorLocal}`, true);
            return;
        }

        if (!arquivoInput || !arquivoAtual || !arquivoInput.files.length) {
            mostrarMensagem("⚠️ Primeiro selecione um arquivo.", true);
            return;
        }

        const origem = document.getElementById("idiomaOrigem")?.value || "pt";
        const destinoSelecionado = document.getElementById("idiomaDestino")?.value;
        if (!destinoSelecionado) {
            mostrarMensagem("⚠️ Selecione o idioma para o qual deseja traduzir.", true);
            return;
        }
        const destino = destinoSelecionado;
        if (origem === destino) {
            mostrarMensagem("⚠️ Selecione idiomas diferentes para a tradução.", true);
            return;
        }

        btnTraduzir.disabled = true;
        if (btnNovo) btnNovo.disabled = true;
        if (btnDemo) btnDemo.disabled = true;
        if (seloDemo) seloDemo.hidden = true;
        slides = [];
        resultadoAtual = null;
        slideAtual = 0;
        renderSlidePreview(0);
        btnTraduzir.innerHTML = '<span class="btn-traduzir-icone" aria-hidden="true">⏳</span> Processando documento...';

        requisicaoTraducao = new AbortController();
        const timeoutTraducao = setTimeout(
            () => requisicaoTraducao?.abort(),
            (tempoMaximoTraducaoSegundos + 5) * 1000
        );
        try {
            const formData = new FormData();
            formData.append("file", arquivoInput.files[0]);
            formData.append("source_lang", origem);
            formData.append("target_lang", destino);

            const response = await fetch("/api/translate", {
                method: "POST",
                body: formData,
                signal: requisicaoTraducao.signal
            });

            const payload = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(payload.error || "Não foi possível concluir a tradução.");
            }

            if (!payload.pages || !payload.pages.length) {
                throw new Error("Nenhuma página foi gerada na tradução.");
            }

            montarResultado(payload);
            mostrarMensagem("✅ Tradução concluída!");

            if (resultado) {
                resultado.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        } catch (erro) {
            console.warn("Falha na tradução:", erro);
            const mensagemErro = erro.name === "AbortError"
                ? "O tempo de espera da tradução foi excedido. O arquivo continua selecionado; você pode tentar novamente."
                : erro instanceof TypeError && erro.message === "Failed to fetch"
                ? "Não foi possível acessar o servidor. Execute iniciar.bat e mantenha as janelas dos serviços abertas."
                : erro.message || "Não foi possível concluir a tradução.";
            mostrarMensagem(`❌ ${mensagemErro}`, true);
        } finally {
            clearTimeout(timeoutTraducao);
            requisicaoTraducao = null;
            btnTraduzir.disabled = false;
            if (btnNovo) btnNovo.disabled = false;
            if (btnDemo) btnDemo.disabled = false;
            btnTraduzir.innerHTML = '<span class="btn-traduzir-icone" aria-hidden="true">✦</span> Traduzir documento <span class="btn-traduzir-seta" aria-hidden="true">→</span>';
        }
    });
}

if (btnAnterior) {
    btnAnterior.addEventListener("click", () => {
        if (!slides.length) return;
        slideAtual = Math.max(0, slideAtual - 1);
        renderSlidePreview(slideAtual);
    });
}

if (btnProximo) {
    btnProximo.addEventListener("click", () => {
        if (!slides.length) return;
        slideAtual = Math.min(slides.length - 1, slideAtual + 1);
        renderSlidePreview(slideAtual);
    });
}

if (btnNovo) {
    btnNovo.addEventListener("click", () => {
        if (requisicaoTraducao) return;
        atualizarArquivo(null);
        mostrarMensagem("Selecione um arquivo e configure os idiomas para começar.");

        slides = [];
        resultadoAtual = null;
        slideAtual = 0;
        renderSlidePreview(0);

        if (nomeResultado) nomeResultado.textContent = "-";
        if (formatoResultado) formatoResultado.textContent = "-";
        if (idiomaResultado) idiomaResultado.textContent = "-";
        if (modoResultado) modoResultado.textContent = "-";
        if (contadorSlides) contadorSlides.textContent = "1 / 1";
        if (seloDemo) seloDemo.hidden = true;
    });
}

if (btnBaixar) {
    btnBaixar.addEventListener("click", async () => {
        if (!resultadoAtual || !resultadoAtual.pages.length) {
            mostrarMensagem("⚠️ Traduza ou carregue uma demonstração antes de baixar.", true);
            return;
        }
        const format = formatoDownload?.value || "txt";
        btnBaixar.disabled = true;
        btnBaixar.textContent = `Gerando ${format.toUpperCase()}...`;
        try {
            const response = await fetch(`/api/download/${encodeURIComponent(format)}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(resultadoAtual)
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || "Não foi possível gerar o arquivo.");
            }
            const blob = await response.blob();
            if (!blob.size) throw new Error("O arquivo gerado está vazio.");
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            const nomeBase = (resultadoAtual.filename || "material")
                .replace(/\.[^.]+$/, "")
                .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_");
            link.href = url;
            link.download = `${nomeBase || "material"}-traduzido.${format}`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            mostrarMensagem(`Arquivo ${format.toUpperCase()} gerado e baixado.`);
        } catch (erro) {
            mostrarMensagem(erro.message || "Não foi possível gerar o arquivo.", true);
        } finally {
            btnBaixar.disabled = false;
            btnBaixar.innerHTML = '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5M4 13v3a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg> Baixar arquivo';
        }
    });
}

renderSlidePreview(0);
