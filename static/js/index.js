// Função para carregar os eventos
async function carregarEventos() {
    try {
        const response = await fetch('/obter_eventos_ativos');
        const data = await response.json();
        
        const container = document.getElementById('eventsContainer');
        const loadingMessage = document.getElementById('loadingMessage');
        
        // Remove a mensagem de carregamento
        loadingMessage.remove();
        
        if (data.eventos && data.eventos.length > 0) {
            data.eventos.forEach(evento => {
                const eventCard = criarCardEvento(evento);
                container.appendChild(eventCard);
            });
        } else {
            container.innerHTML = `
                <div class="no-events">
                    <h3>🏃‍♂️ Nenhum evento ativo no momento</h3>
                    <p>Fique ligado! Novos eventos serão anunciados em breve.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar eventos:', error);
        const container = document.getElementById('eventsContainer');
        const loadingMessage = document.getElementById('loadingMessage');
        loadingMessage.remove();
        
        container.innerHTML = `
            <div class="no-events">
                <h3>❌ Erro ao carregar eventos</h3>
                <p>Tente recarregar a página.</p>
            </div>
        `;
    }
}

// Função para criar o card do evento
function criarCardEvento(evento) {
    const card = document.createElement('div');
    card.className = 'event-card';
    
    card.innerHTML = `
        <img src="/static/img/${evento.IDEVENTO}.jpeg" 
             alt="Imagem do evento ${evento.DESCRICAO}" 
             class="event-image"
             onerror="this.src='/static/img/default-event.jpg'">
        
        <div class="event-info">
            <h3 class="event-title">${evento.DESCRICAO}</h3>
            <div class="event-date">Data do Evento: ${evento.DTEVENTO}</div>
            <div class="event-inscription">Inscrições: ${evento.PERIODO_INSCRICAO}</div>
            <button class="more-info-btn" onclick="window.location.href='${evento.ROTA}'">
                Mais Informações
            </button>
        </div>
    `;
    
    return card;
}

// Carrega os eventos quando a página carrega
document.addEventListener('DOMContentLoaded', carregarEventos);