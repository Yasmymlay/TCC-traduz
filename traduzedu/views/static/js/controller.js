// =====================================
// CONTROLLER (frontend)
// Liga os eventos da View às ações do Model.
// =====================================

(() => {
    const model = TraduzEduModel;
    const view = TraduzEduView;
    const { el } = view;
    const estado = model.estado;

    const arquivoAbertoDiretamente = window.location.protocol === "file:";
    const avisoServidorLocal = "Para traduzir, feche esta página, execute iniciar.bat na pasta do projeto e use o endereço http://127.0.0.1:5001 que será aberto.";

    // ---------- Status dos serviços ----------

    async function atualizarStatusMecanismos() {
        if (!el.statusMecanismos) return;
        try {
            const { ativos, configurados } = await model.buscarStatusMecanismos();
            const detalhes = [];
            if (ativos.length) detalhes.push(`Disponíveis: ${ativos.join(", ")}.`);
            if (configurados.length) detalhes.push(`Configurados: ${configurados.join(", ")}.`);
            if (detalhes.length) {
                view.mostrarStatus(el.statusMecanismos, detalhes.join(" "));
            } else {
                view.mostrarStatus(el.statusMecanismos, "Tradutores indisponíveis. Você ainda pode usar a demonstração offline.", true);
            }
        } catch (erro) {
            view.mostrarStatus(
                el.statusMecanismos,
                erro.name === "AbortError"
                    ? "A verificação dos tradutores demorou demais; você ainda pode tentar traduzir ou abrir a demonstração."
                    : `Não foi possível verificar os tradutores: ${erro.message || "erro de comunicação"}`,
                true
            );
        }
    }

    async function atualizarStatusOCR() {
        if (!el.statusOCR) return;
        try {
            const status = await model.buscarStatusOCR(view.parIdiomas().source);
            if (!status.ok || !status.available || status.missing_languages?.length) {
                view.mostrarStatus(el.statusOCR, status.error || "OCR indisponível neste computador.", true);
                return;
            }
            view.mostrarStatus(
                el.statusOCR,
                `OCR disponível (${status.version}; idiomas: ${status.languages.join(", ")}). PDFs digitalizados serão reconhecidos automaticamente.`
            );
        } catch (erro) {
            view.mostrarStatus(el.statusOCR, `Não foi possível verificar o OCR: ${erro.message || "erro de comunicação"}`, true);
        }
    }

    async function atualizarStatusArgos() {
        if (!el.statusModelosArgos) return;
        el.statusModelosArgos.textContent = "Verificando modelos locais...";
        if (el.btnInstalarModelo) el.btnInstalarModelo.hidden = true;
        try {
            view.mostrarStatusArgos(await model.buscarModelosArgos(view.parIdiomas()));
        } catch (erro) {
            el.statusModelosArgos.textContent = erro.message || "Não foi possível verificar os modelos Argos.";
        }
    }

    async function consultarCatalogoArgos() {
        view.definirBotao(el.btnVerificarCatalogo, true, "Consultando catálogo...");
        try {
            view.mostrarStatusArgos(await model.consultarCatalogoArgos(view.parIdiomas()));
            view.mostrarMensagem("Catálogo Argos consultado. Essa verificação não baixa modelos de tradução.");
        } catch (erro) {
            view.mostrarMensagem(erro.message || "Não foi possível consultar o catálogo Argos.", true);
        } finally {
            view.definirBotao(el.btnVerificarCatalogo, false, "Consultar catálogo Argos");
        }
    }

    async function instalarModeloArgos() {
        const par = view.parIdiomas();
        const confirmacao = `O modelo Argos ${par.source} → ${par.target} será baixado do catálogo verificado `
            + "e instalado neste computador. Deseja continuar?";
        if (!window.confirm(confirmacao)) return;

        view.definirBotao(el.btnInstalarModelo, true, "Baixando e instalando...");
        try {
            view.mostrarStatusArgos(await model.instalarModeloArgos(par));
            view.mostrarMensagem(`Modelo Argos ${par.source} → ${par.target} instalado e verificado.`);
        } catch (erro) {
            view.mostrarMensagem(erro.message || "Não foi possível instalar o modelo Argos.", true);
        } finally {
            view.definirBotao(el.btnInstalarModelo, false);
        }
    }

    // ---------- Seleção do arquivo ----------

    function selecionarArquivo(arquivo) {
        estado.arquivoAtual = arquivo || null;
        if (!arquivo) {
            view.mostrarArquivo(null);
            return;
        }
        const erro = model.validarArquivo(arquivo);
        if (erro) {
            view.mostrarMensagem(`❌ ${erro}`, true);
            selecionarArquivo(null);
            return;
        }
        view.mostrarArquivo(arquivo);
        view.mostrarMensagem("✅ Arquivo selecionado.");
    }

    // ---------- Resultado ----------

    function exibirResultado(payload) {
        const arquivo = view.arquivoDoInput();
        const par = view.parIdiomas();
        const nomeArquivo = arquivo ? arquivo.name : payload?.filename || "-";
        const origem = payload?.source_lang || par.source;
        const destino = payload?.target_lang || par.target;

        view.mostrarResumo({
            nomeArquivo,
            origem,
            destino,
            modo: payload?.demo ? "Demonstração preparada" : view.modoSelecionado()
        });
        view.mostrarSeloDemo(Boolean(payload?.demo));
        model.definirResultado(payload, {
            nomeArquivo: arquivo ? arquivo.name : payload?.filename || "material",
            origem: par.source,
            destino: par.target
        });
        view.renderizarSlide(estado.slides, estado.slideAtual);
    }

    // ---------- Ações principais ----------

    async function traduzir() {
        if (arquivoAbertoDiretamente) {
            view.mostrarMensagem(`⚠️ ${avisoServidorLocal}`, true);
            return;
        }
        const arquivo = view.arquivoDoInput();
        if (!estado.arquivoAtual || !arquivo) {
            view.mostrarMensagem("⚠️ Primeiro selecione um arquivo.", true);
            return;
        }
        const { source: origem, target: destino } = view.parIdiomas();
        if (!destino) {
            view.mostrarMensagem("⚠️ Selecione o idioma para o qual deseja traduzir.", true);
            return;
        }
        if (origem === destino) {
            view.mostrarMensagem("⚠️ Selecione idiomas diferentes para a tradução.", true);
            return;
        }

        view.definirTraduzindo(true);
        view.mostrarSeloDemo(false);
        model.limparResultado();
        view.renderizarSlide(estado.slides, 0);
        try {
            const payload = await model.traduzir(arquivo, origem, destino);
            exibirResultado(payload);
            const avisos = payload.warnings || [];
            view.mostrarMensagem(
                avisos.length ? `✅ Tradução concluída. ⚠️ ${avisos.join(" ")}` : "✅ Tradução concluída!"
            );
            view.rolarParaResultado();
        } catch (erro) {
            console.warn("Falha na tradução:", erro);
            const mensagemErro = erro.name === "AbortError"
                ? "O tempo de espera da tradução foi excedido. O arquivo continua selecionado; você pode tentar novamente."
                : erro instanceof TypeError && erro.message === "Failed to fetch"
                    ? "Não foi possível acessar o servidor. Execute iniciar.bat e mantenha as janelas dos serviços abertas."
                    : erro.message || "Não foi possível concluir a tradução.";
            view.mostrarMensagem(`❌ ${mensagemErro}`, true);
        } finally {
            view.definirTraduzindo(false);
        }
    }

    async function carregarDemonstracao() {
        view.definirBotao(el.btnDemo, true, "Carregando exemplo...");
        try {
            const payload = await model.buscarDemonstracao("pdf");
            selecionarArquivo(null);
            view.definirIdiomas(payload.source_lang, payload.target_lang);
            exibirResultado(payload);
            view.mostrarMensagem("Modo demonstração: este resultado preparado não é uma tradução do seu arquivo.");
            view.rolarParaResultado();
        } catch (erro) {
            view.mostrarMensagem(`❌ ${erro.message || "Não foi possível carregar a demonstração."}`, true);
        } finally {
            view.definirBotao(el.btnDemo, false, "Carregar demonstração");
        }
    }

    function novoDocumento() {
        if (estado.requisicaoTraducao) return;
        selecionarArquivo(null);
        view.mostrarMensagem("Selecione um arquivo e configure os idiomas para começar.");
        model.limparResultado();
        view.renderizarSlide(estado.slides, 0);
        view.limparResumo();
    }

    async function baixar() {
        if (!estado.resultadoAtual || !estado.resultadoAtual.pages.length) {
            view.mostrarMensagem("⚠️ Traduza ou carregue uma demonstração antes de baixar.", true);
            return;
        }
        const formato = view.formatoDownload();
        view.definirBaixando(formato);
        try {
            const { blob, nome } = await model.gerarDownload(formato);
            view.salvarArquivo(blob, nome);
            view.mostrarMensagem(`Arquivo ${formato.toUpperCase()} gerado e baixado.`);
        } catch (erro) {
            view.mostrarMensagem(erro.message || "Não foi possível gerar o arquivo.", true);
        } finally {
            view.definirBaixando(null);
        }
    }

    function navegar(deslocamento) {
        if (model.irParaSlide(deslocamento)) {
            view.renderizarSlide(estado.slides, estado.slideAtual);
        }
    }

    // ---------- Registro dos eventos ----------

    function registrarEventos() {
        el.arquivoInput?.addEventListener("change", () => selecionarArquivo(view.arquivoDoInput()));

        if (el.uploadArea) {
            for (const evento of ["dragenter", "dragover"]) {
                el.uploadArea.addEventListener(evento, (event) => {
                    event.preventDefault();
                    view.marcarArraste(true);
                });
            }
            for (const evento of ["dragleave", "drop"]) {
                el.uploadArea.addEventListener(evento, (event) => {
                    event.preventDefault();
                    view.marcarArraste(false);
                });
            }
            el.uploadArea.addEventListener("drop", (event) => {
                const arquivo = event.dataTransfer?.files[0];
                if (!arquivo || !el.arquivoInput) return;
                view.colocarArquivoNoInput(arquivo);
                selecionarArquivo(arquivo);
            });
        }

        for (const select of [el.idiomaOrigem, el.idiomaDestino]) {
            select?.addEventListener("change", () => {
                atualizarStatusArgos();
                atualizarStatusOCR();
            });
        }

        el.btnTraduzir?.addEventListener("click", traduzir);
        el.btnDemo?.addEventListener("click", carregarDemonstracao);
        el.btnVerificarCatalogo?.addEventListener("click", consultarCatalogoArgos);
        el.btnInstalarModelo?.addEventListener("click", instalarModeloArgos);
        el.btnAnterior?.addEventListener("click", () => navegar(-1));
        el.btnProximo?.addEventListener("click", () => navegar(1));
        el.btnNovo?.addEventListener("click", novoDocumento);
        el.btnBaixar?.addEventListener("click", baixar);
    }

    // ---------- Inicialização ----------

    if (arquivoAbertoDiretamente) {
        view.mostrarMensagem(`⚠️ ${avisoServidorLocal}`, true);
    }
    registrarEventos();
    view.renderizarSlide(estado.slides, 0);
    atualizarStatusMecanismos();
    atualizarStatusArgos();
    atualizarStatusOCR();
})();
