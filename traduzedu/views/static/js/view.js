// =====================================
// VIEW (frontend)
// Leitura e atualização dos elementos da página. Não conversa com a API.
// =====================================

const TraduzEduView = (() => {
    const $ = (id) => document.getElementById(id);

    const el = {
        arquivoInput: $("arquivo"),
        arquivoSelecionado: $("arquivoSelecionado"),
        uploadArea: document.querySelector(".upload-area"),
        idiomaOrigem: $("idiomaOrigem"),
        idiomaDestino: $("idiomaDestino"),
        btnTraduzir: $("btnTraduzir"),
        resultado: $("resultado"),
        mensagem: $("mensagem"),
        nomeResultado: $("nomeResultado"),
        formatoResultado: $("formatoResultado"),
        idiomaResultado: $("idiomaResultado"),
        modoResultado: $("modoResultado"),
        visualizacao: $("visualizacao"),
        btnBaixar: $("btnBaixar"),
        btnNovo: $("btnNovo"),
        btnAnterior: $("btnAnterior"),
        btnProximo: $("btnProximo"),
        contadorSlides: $("contadorSlides"),
        btnDemo: $("btnDemo"),
        seloDemo: $("seloDemo"),
        statusMecanismos: $("statusMecanismos"),
        statusOCR: $("statusOCR"),
        statusModelosArgos: $("statusModelosArgos"),
        btnVerificarCatalogo: $("btnVerificarCatalogo"),
        btnInstalarModelo: $("btnInstalarModelo"),
        formatoDownload: $("formatoDownload")
    };

    const HTML_BTN_TRADUZIR = '<span class="btn-traduzir-icone" aria-hidden="true">✦</span> Traduzir documento <span class="btn-traduzir-seta" aria-hidden="true">→</span>';
    const HTML_BTN_TRADUZINDO = '<span class="btn-traduzir-icone" aria-hidden="true">⏳</span> Processando documento...';
    const HTML_BTN_BAIXAR = '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M10 3v9m0 0 3.5-3.5M10 12 6.5 8.5M4 13v3a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg> Baixar arquivo';
    const HTML_RESULTADO_VAZIO = `
        <div class="resultado-vazio">
            <span class="resultado-vazio-icone" aria-hidden="true">
                <svg viewBox="0 0 52 52" fill="none"><rect x="7" y="7" width="38" height="38" rx="14" stroke="currentColor" stroke-width="1.6" /><path d="M17 20h18M17 26h18M17 32h11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
            </span>
            <strong>Seu resultado aparecerá aqui</strong>
            <span>Envie um documento para visualizar o conteúdo traduzido.</span>
        </div>
    `;

    function escapeHtml(value = "") {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // ---------- Leitura dos campos ----------

    function parIdiomas() {
        return {
            source: el.idiomaOrigem?.value || "pt",
            target: el.idiomaDestino?.value || "en"
        };
    }

    function definirIdiomas(origem, destino) {
        if (el.idiomaOrigem) el.idiomaOrigem.value = origem;
        if (el.idiomaDestino) el.idiomaDestino.value = destino;
    }

    function arquivoDoInput() {
        return el.arquivoInput?.files[0] || null;
    }

    function formatoDownload() {
        return el.formatoDownload?.value || "txt";
    }

    function modoSelecionado() {
        const modo = document.querySelector('input[name="modo"]:checked');
        return modo ? modo.parentElement.querySelector("strong").textContent : "Tradução completa";
    }

    // ---------- Mensagens e status ----------

    function mostrarMensagem(texto, erro = false) {
        if (!el.mensagem) return;
        el.mensagem.textContent = texto;
        el.mensagem.classList.toggle("is-error", erro);
        el.mensagem.classList.toggle("is-success", !erro);
    }

    function mostrarStatus(elemento, texto, erro = false) {
        if (!elemento) return;
        elemento.textContent = texto;
        elemento.classList.toggle("is-error", erro);
    }

    function mostrarStatusArgos(payload) {
        if (!el.statusModelosArgos) return;
        if (el.btnInstalarModelo) el.btnInstalarModelo.hidden = true;
        const par = `${payload.source} → ${payload.target}`;
        if (payload.installed) {
            el.statusModelosArgos.textContent = `O par ${par} já está instalado e disponível localmente.`;
            return;
        }
        if (!payload.catalog_checked) {
            el.statusModelosArgos.textContent = `O par ${par} não está instalado. Consulte o catálogo online para verificar se o modelo está disponível; nenhum modelo será baixado nessa consulta.`;
            return;
        }
        if (payload.package_available) {
            el.statusModelosArgos.textContent = `Modelo ${par}, versão ${payload.package_version}, disponível em ${payload.download_host || "catálogo Argos"}. A instalação só começa depois de sua confirmação.`;
            if (el.btnInstalarModelo) {
                el.btnInstalarModelo.textContent = `Instalar ${par}`;
                el.btnInstalarModelo.hidden = false;
            }
            return;
        }
        el.statusModelosArgos.textContent = `O catálogo consultado não oferece o modelo direto ${par}. Nenhum modelo foi baixado.`;
    }

    // ---------- Arquivo selecionado ----------

    function mostrarArquivo(arquivo) {
        if (!arquivo) {
            if (el.arquivoInput) el.arquivoInput.value = "";
            if (el.arquivoSelecionado) {
                el.arquivoSelecionado.innerHTML = '<span class="arquivo-vazio-icone" aria-hidden="true">+</span><span>Nenhum arquivo selecionado</span>';
            }
            el.uploadArea?.classList.remove("is-filled");
            return;
        }
        if (el.arquivoSelecionado) {
            el.arquivoSelecionado.innerHTML = `📄 <strong>${escapeHtml(arquivo.name)}</strong>`;
        }
        el.uploadArea?.classList.add("is-filled");
    }

    function colocarArquivoNoInput(arquivo) {
        if (!el.arquivoInput) return;
        const transfer = new DataTransfer();
        transfer.items.add(arquivo);
        el.arquivoInput.files = transfer.files;
    }

    function marcarArraste(ativo) {
        el.uploadArea?.classList.toggle("is-dragging", ativo);
    }

    // ---------- Resultado ----------

    function renderizarBloco(block) {
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
    }

    function renderizarSlide(slides, index) {
        if (!el.visualizacao) return;
        if (!slides.length) {
            el.visualizacao.innerHTML = HTML_RESULTADO_VAZIO;
            if (el.contadorSlides) el.contadorSlides.textContent = "1 / 1";
            return;
        }

        const slide = slides[index] || slides[0];
        const pageTitle = slide.page_title || `Página ${index + 1}`;
        const documentTitle = slide.title || "Material traduzido";
        const subtitle = slide.subtitle || "";
        const itensHtml = (slide.blocks || []).map(renderizarBloco).join("");
        const meta = `${slide.formato || "PDF"} • ${slide.source_lang || "pt"} → ${slide.target_lang || "es"}`;

        el.visualizacao.innerHTML = `
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

                    <div class="slide-meta">${escapeHtml(meta)}</div>
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

        if (el.contadorSlides) el.contadorSlides.textContent = `${index + 1} / ${slides.length}`;
        if (el.btnAnterior) el.btnAnterior.disabled = index === 0;
        if (el.btnProximo) el.btnProximo.disabled = index >= slides.length - 1;
    }

    function mostrarResumo({ nomeArquivo, origem, destino, modo }) {
        if (el.nomeResultado) el.nomeResultado.textContent = nomeArquivo || "-";
        if (el.formatoResultado) {
            el.formatoResultado.textContent = nomeArquivo ? nomeArquivo.split(".").pop().toUpperCase() : "-";
        }
        if (el.idiomaResultado) {
            el.idiomaResultado.textContent = `${TraduzEduModel.nomeIdioma(origem)} → ${TraduzEduModel.nomeIdioma(destino)}`;
        }
        if (el.modoResultado) el.modoResultado.textContent = modo || "Tradução completa";
    }

    function limparResumo() {
        for (const elemento of [el.nomeResultado, el.formatoResultado, el.idiomaResultado, el.modoResultado]) {
            if (elemento) elemento.textContent = "-";
        }
        if (el.contadorSlides) el.contadorSlides.textContent = "1 / 1";
        mostrarSeloDemo(false);
    }

    function mostrarSeloDemo(visivel) {
        if (el.seloDemo) el.seloDemo.hidden = !visivel;
    }

    function rolarParaResultado() {
        el.resultado?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // ---------- Estados dos botões ----------

    function definirTraduzindo(ativo) {
        if (el.btnTraduzir) {
            el.btnTraduzir.disabled = ativo;
            el.btnTraduzir.innerHTML = ativo ? HTML_BTN_TRADUZINDO : HTML_BTN_TRADUZIR;
        }
        if (el.btnNovo) el.btnNovo.disabled = ativo;
        if (el.btnDemo) el.btnDemo.disabled = ativo;
    }

    function definirBotao(botao, desabilitado, texto) {
        if (!botao) return;
        botao.disabled = desabilitado;
        if (texto !== undefined) botao.textContent = texto;
    }

    function definirBaixando(formato) {
        if (!el.btnBaixar) return;
        el.btnBaixar.disabled = Boolean(formato);
        if (formato) {
            el.btnBaixar.textContent = `Gerando ${formato.toUpperCase()}...`;
        } else {
            el.btnBaixar.innerHTML = HTML_BTN_BAIXAR;
        }
    }

    function salvarArquivo(blob, nome) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = nome;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    return {
        el,
        parIdiomas,
        definirIdiomas,
        arquivoDoInput,
        formatoDownload,
        modoSelecionado,
        mostrarMensagem,
        mostrarStatus,
        mostrarStatusArgos,
        mostrarArquivo,
        colocarArquivoNoInput,
        marcarArraste,
        renderizarSlide,
        mostrarResumo,
        limparResumo,
        mostrarSeloDemo,
        rolarParaResultado,
        definirTraduzindo,
        definirBotao,
        definirBaixando,
        salvarArquivo
    };
})();
