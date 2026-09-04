function mudarIdioma(idioma) {
    // Busca todos os elementos que possuem texto traduzível
    const elementosTraduziveis = document.querySelectorAll('[data-pt]');

    elementosTraduziveis.forEach(elemento => {
        if (idioma === 'es') {
            // Substitui o texto pelo equivalente em espanhol
            elemento.textContent = elemento.getAttribute('data-es');
        } else {
            // Volta o texto para o original em português
            elemento.textContent = elemento.getAttribute('data-pt');
        }
    });

    // Controla o visual ativo dos botões de idioma
    document.getElementById('btn-pt').classList.remove('active');
    document.getElementById('btn-es').classList.remove('active');

    if (idioma === 'es') {
        document.getElementById('btn-es').classList.add('active');
    } else {
        document.getElementById('btn-pt').classList.add('active');
    }
}
// Seleciona todos os botões de idioma
const botoesIdioma = document.querySelectorAll('.lang-btn');

// Função que realiza a troca de textos na página
function alternarIdioma(idiomaSelecionado) {
  // Busca todos os elementos que possuem tradução configurada
  const elementosTraduziveis = document.querySelectorAll('[data-pt]');

  elementosTraduziveis.forEach(elemento => {
    // Obtém o texto correspondente ao idioma clicado
    const textoTraduzido = elemento.getAttribute(`data-${idiomaSelecionado}`);
    
    if (textoTraduzido) {
      elemento.textContent = textoTraduzido;
    }
  });

  // Atualiza o visual dos botões (muda qual botão fica branco/ativo)
  botoesIdioma.forEach(botao => {
    if (botao.getAttribute('data-lang') === idiomaSelecionado) {
      botao.classList.add('active');
    } else {
      botao.classList.remove('active');
    }
  });
}

// Adiciona o evento de clique em cada um dos botões
botoesIdioma.forEach(botao => {
  botao.addEventListener('click', () => {
    const idioma = botao.getAttribute('data-lang');
    alternarIdioma(idioma);
  });
});