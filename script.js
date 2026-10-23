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

// =====================================
// VARIÁVEIS
// =====================================

let arquivoAtual = null;
let slides = [];
let slideAtual = 0;
let idiomaAtivo = "pt";

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
    mensagem.style.background = erro ? "rgba(190, 60, 60, 0.08)" : "rgba(18, 115, 89, 0.06)";
    mensagem.style.color = erro ? "#7d2b2b" : "#245d5c";
}

function renderSlidePreview(index = 0) {
    if (!slides.length || !visualizacao) {
        if (visualizacao) {
            visualizacao.innerHTML = "O conteúdo do arquivo aparecerá aqui.";
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
        const isListItem = type === "list-item" || /^(?:[a-zA-Z]|\d+)[\).]/.test(text.trim());

        if (isListItem) {
            const headingMatch = text.match(/^([^:]{0,80})[:\-]?\s*(.*)$/);
            const heading = headingMatch ? escapeHtml(headingMatch[1].trim()) : "";
            const content = headingMatch ? escapeHtml(headingMatch[2].trim()) : "";

            if (content) {
                return `
                    <div class="slide-item">
                        <strong>${heading || text}</strong>
                        <p>${content}</p>
                    </div>
                `;
            }

            return `
                <div class="slide-item">
                    <strong>${text}</strong>
                </div>
            `;
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
                        ${itensHtml}
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

    const modoTexto = modoSelecionado ? modoSelecionado.parentElement.querySelector("strong").textContent : "Tradução completa";
    atualizarResumoArquivo(arquivo ? arquivo.name : payload?.filename || "-", origem, destino, modoTexto);

    slides = Array.isArray(payload?.pages) ? payload.pages.map((page) => ({
        ...page,
        formato: (arquivo ? arquivo.name : payload?.filename || "arquivo").split('.').pop().toUpperCase(),
        source_lang: payload?.source_lang || origem,
        target_lang: payload?.target_lang || destino,
    })) : [];

    slideAtual = 0;
    renderSlidePreview(slideAtual);
}

// =====================================
// SELEÇÃO DO ARQUIVO
// =====================================

if (arquivoInput) {
    arquivoInput.addEventListener("change", function () {
        arquivoAtual = this.files[0];

        if (!arquivoAtual) {
            if (arquivoSelecionado) {
                arquivoSelecionado.innerHTML = '<span>📄</span> Nenhum arquivo selecionado';
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
                arquivoSelecionado.innerHTML = '<span>📄</span> Formato não permitido';
            }
            arquivoAtual = null;
            this.value = "";
            return;
        }

        if (arquivoSelecionado) {
            arquivoSelecionado.innerHTML = `📄 <strong>${escapeHtml(arquivoAtual.name)}</strong>`;
        }

        const uploadArea = document.querySelector(".upload-area");
        if (uploadArea) {
            uploadArea.classList.add("is-filled");
        }

        mostrarMensagem("✅ Arquivo selecionado.");
    });
}

// =====================================
// BOTÃO TRADUZIR
// =====================================

if (btnTraduzir) {
    btnTraduzir.addEventListener("click", async function () {
        if (!arquivoInput || !arquivoInput.files.length) {
            mostrarMensagem("⚠️ Primeiro selecione um arquivo.", true);
            return;
        }

        const origem = document.getElementById("idiomaOrigem")?.value || "pt";
        const destino = document.getElementById("idiomaDestino")?.value || "en";

        btnTraduzir.disabled = true;
        btnTraduzir.innerHTML = "<span>⏳</span> Processando...";

        try {
            const formData = new FormData();
            formData.append("file", arquivoInput.files[0]);
            formData.append("source_lang", origem);
            formData.append("target_lang", destino);

            const response = await fetch("/api/translate", {
                method: "POST",
                body: formData
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
            console.error("Erro na tradução:", erro);
            mostrarMensagem(`❌ ${erro.message || "Não foi possível concluir a tradução."}`, true);
        } finally {
            btnTraduzir.disabled = false;
            btnTraduzir.innerHTML = '<span>✨</span> Traduzir agora <span>→</span>';
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
        if (arquivoInput) arquivoInput.value = "";
        if (arquivoSelecionado) arquivoSelecionado.innerHTML = '<span>📄</span> Nenhum arquivo selecionado';
        if (mensagem) mensagem.textContent = "Selecione um arquivo e configure os idiomas para começar.";

        slides = [];
        slideAtual = 0;
        renderSlidePreview(0);

        if (nomeResultado) nomeResultado.textContent = "-";
        if (formatoResultado) formatoResultado.textContent = "-";
        if (idiomaResultado) idiomaResultado.textContent = "-";
        if (modoResultado) modoResultado.textContent = "-";
        if (contadorSlides) contadorSlides.textContent = "1 / 1";
    });
}

if (btnBaixar) {
    btnBaixar.addEventListener("click", () => {
        if (!slides.length) {
            mostrarMensagem("⚠️ Traduza um arquivo antes de baixar o conteúdo.", true);
            return;
        }

        const texto = slides.map((slide) => {
            const parts = [slide.page_title || '', slide.subtitle || '', ...(slide.blocks || []).map((block) => block.text || '')].filter(Boolean);
            return parts.join('\n\n');
        }).join('\n\n');

        const blob = new Blob([texto], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "tradução.txt";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    });
}

renderSlidePreview(0);
