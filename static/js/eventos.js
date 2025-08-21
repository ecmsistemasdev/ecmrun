// Variáveis globais
let descricaoContent = '';
let regulamentoContent = '';
let editingEventId = null;

let lotes = [];
let lotesCounter = 0;
let editingLotes = false;
let bannerData = null;

let itensDoEvento = [];
let lotesDoItem = [];
let itemAtual = null;
let editandoItem = false;
let editandoLote = false;

let imagensDoEvento = [];
let imagemAtual = null;
let editandoImagem = false;
let imagemData = null;   

// Função de autenticação
document.getElementById('authForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const senha = document.getElementById('senha').value;
    
    try {
        const response = await fetch('/api/auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ senha: senha })
        });
        
        if (response.ok) {
            document.getElementById('authScreen').classList.add('hidden');
            document.getElementById('mainScreen').classList.remove('hidden');
            loadEventsList();
        } else {
            showMessage('Senha incorreta!', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão. Tente novamente.', 'error');
    }
});

// Função de logout
function logout() {
    document.getElementById('authScreen').classList.remove('hidden');
    document.getElementById('mainScreen').classList.add('hidden');
    document.getElementById('senha').value = '';
    showEventsList();
}

// Função para mostrar lista de eventos
function showEventsList() {
    document.getElementById('eventsListScreen').classList.remove('hidden');
    document.getElementById('eventFormScreen').classList.add('hidden');
    loadEventsList();
}

// Função para mostrar formulário de criação
function showCreateForm() {
    document.getElementById('eventsListScreen').classList.add('hidden');
    document.getElementById('eventFormScreen').classList.remove('hidden');
    document.getElementById('formTitle').textContent = 'Novo Evento';
    document.getElementById('submitBtn').textContent = 'Salvar Evento';
    document.getElementById('eventoForm').reset();
    editingEventId = null;
    descricaoContent = '';
    regulamentoContent = '';
    bannerData = null; // Reset banner data
    document.getElementById('descricaoEditor').innerHTML = '';
    document.getElementById('regulamentoEditor').innerHTML = '';
    document.getElementById('linkPreview').textContent = '[seu-link]';
    removeBanner(); // Remove qualquer banner preview
}

// Função para carregar lista de eventos
async function loadEventsList() {
    try {
        const response = await fetch('/api/eventos?idorganizador=' + getIdOrganizador());
        const eventos = await response.json();
        
        const listContainer = document.getElementById('eventsList');
        
        if (eventos.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <h3>Nenhum evento encontrado</h3>
                    <p>Clique em "Novo Evento" para criar seu primeiro evento</p>
                </div>
            `;
        } else {
            listContainer.innerHTML = eventos.map(evento => `
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-title">${evento.titulo}</div>
                        <div class="event-details">
                            ${evento.datainicio} a ${evento.datafim}
                            ${evento.endereco ? ' • ' + evento.endereco : ''}
                        </div>
                    </div>
                    <div class="event-actions">
                        <span class="event-status ${evento.ativo === 'S' ? 'status-active' : 'status-inactive'}">
                            ${evento.ativo === 'S' ? 'Ativo' : 'Inativo'}
                        </span>
                        <button type="button" class="btn btn-primary btn-sm" onclick="editEvent(${evento.idevento})">
                            Editar
                        </button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="viewEvent('${evento.dslink}')">
                            Visualizar
                        </button>
                        ${evento.ativo === 'S' ? 
                            `<button type="button" class="btn btn-danger btn-sm" onclick="deactivateEvent(${evento.idevento})">Desativar</button>` :
                            ''
                        }
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        showMessage('Erro ao carregar eventos.', 'error');
    }
}

// Função para editar evento
async function editEvent(eventoId) {
    try {
        const response = await fetch(`/api/eventos/${eventoId}`);
        const evento = await response.json();
        
        console.log('Dados do evento carregados:', evento); // Debug
        
        if (response.ok) {
            editingEventId = eventoId;
            document.getElementById('eventsListScreen').classList.add('hidden');
            document.getElementById('eventFormScreen').classList.remove('hidden');
            document.getElementById('formTitle').textContent = 'Editar Evento';
            document.getElementById('submitBtn').textContent = 'Atualizar Evento';
            
            // Preencher formulário
            Object.keys(evento).forEach(key => {
                const field = document.getElementById(key);
                if (field && evento[key] !== null && key !== 'banner') {
                    field.value = evento[key];
                }
            });
            
            descricaoContent = evento.descricao || '';
            regulamentoContent = evento.regulamento || '';
            document.getElementById('descricaoEditor').innerHTML = descricaoContent;
            document.getElementById('regulamentoEditor').innerHTML = regulamentoContent;
            document.getElementById('linkPreview').textContent = evento.dslink || '[seu-link]';
            
            // Carregar banner se existir
            console.log('Banner do evento:', evento.banner ? 'existe' : 'não existe'); // Debug

            if (evento.banner) {
                const bannerSrc = `data:image/jpeg;base64,${evento.banner}`;
                document.getElementById('bannerImage').src = bannerSrc;
                document.getElementById('bannerPreview').style.display = 'block';
                bannerData = bannerSrc;
                
                // ADICIONAR ESTA LINHA:
                updateFileInputLabel();
                
                console.log('Banner carregado com sucesso'); // Debug
            } else {
                removeBanner();
                console.log('Nenhum banner encontrado'); // Debug
            }
        } else {
            showMessage('Erro ao carregar evento.', 'error');
        }
    } catch (error) {
        console.error('Erro ao carregar evento:', error);
        showMessage('Erro de conexão.', 'error');
    }
}
// Função para visualizar evento
function viewEvent(dslink) {
    window.open(`/evento/${dslink}`, '_blank');
}

// Função para desativar evento
async function deactivateEvent(eventoId) {
    if (confirm('Tem certeza que deseja desativar este evento?')) {
        try {
            const response = await fetch(`/api/eventos/${eventoId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showMessage('Evento desativado com sucesso!', 'success');
                loadEventsList();
            } else {
                showMessage('Erro ao desativar evento.', 'error');
            }
        } catch (error) {
            showMessage('Erro de conexão.', 'error');
        }
    }
}

// Função para validar e formatar o campo dslink
document.getElementById('dslink').addEventListener('input', function(e) {
    let value = e.target.value;
    value = value.toLowerCase().replace(/[^a-z0-9-]/g, '');
    e.target.value = value;
    document.getElementById('linkPreview').textContent = value || '[seu-link]';
});


function openModal(modalId) {
    console.log('=== openModal EXECUTADA ===');
    console.log('modalId:', modalId);
    console.log('Timestamp:', new Date().toLocaleTimeString());
    
    try {
        if (modalId === 'imagensModal') {
            console.log('Chamando openImagensModal...');
            openImagensModal();
            return;
        }
        
        if (modalId === 'lotesModal') {
            console.log('Chamando openLotesModal...');
            openLotesModal();
            return;
        }
        
        // Modal padrão
        console.log('Abrindo modal padrão:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
            console.log('Modal padrão aberto com sucesso');
        } else {
            console.error('Modal não encontrado:', modalId);
        }
        
    } catch (error) {
        console.error('ERRO em openModal:', error);
        alert('Erro ao abrir modal: ' + error.message);
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Fechar modal ao clicar fora
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Funções do editor de texto
function formatText(command, value = null) {
    document.execCommand(command, false, value);
}

function saveEditor(type) {
    if (type === 'descricao') {
        descricaoContent = document.getElementById('descricaoEditor').innerHTML;
        closeModal('descricaoModal');
        showMessage('Descrição salva com sucesso!', 'success');
    } else if (type === 'regulamento') {
        regulamentoContent = document.getElementById('regulamentoEditor').innerHTML;
        closeModal('regulamentoModal');
        showMessage('Regulamento salvo com sucesso!', 'success');
    }
}

// Função para mostrar mensagens
function showMessage(message, type) {
    const messagesDiv = document.getElementById('messages');
    const messageClass = type === 'success' ? 'success-message' : 'error-message';
    messagesDiv.innerHTML = `<div class="${messageClass}">${message}</div>`;
    
    // Remove a mensagem após 5 segundos
    setTimeout(() => {
        messagesDiv.innerHTML = '';
    }, 5000);
}

// Função para obter ID do organizador
function getIdOrganizador() {
    // Simular ID do organizador (em uma aplicação real, viria do sistema de autenticação)
    return '1';
}

// Submissão do formulário
document.getElementById('eventoForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {};
    
    // Coletar dados do formulário
    for (let [key, value] of formData.entries()) {
        if (key !== 'eventoId') {
            data[key] = value;
        }
    }

    // Adicionar conteúdos dos editores
    data.descricao = descricaoContent;
    data.regulamento = regulamentoContent;
    data.idorganizador = getIdOrganizador();
    data.ativo = 'S';
    
    // Adicionar banner se houver
    if (bannerData) {
        data.banner = bannerData;
    }

    // Validações
    if (!data.titulo || !data.datainicio || !data.datafim || !data.dslink) {
        showMessage('Por favor, preencha todos os campos obrigatórios.', 'error');
        return;
    }

    if (new Date(data.datafim) < new Date(data.datainicio)) {
        showMessage('A data de fim deve ser posterior à data de início.', 'error');
        return;
    }

    try {
        let response;
        let method = 'POST';
        let url = '/api/eventos';
        
        if (editingEventId) {
            method = 'PUT';
            url = `/api/eventos/${editingEventId}`;
        }

        response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            const message = editingEventId ? 'Evento atualizado com sucesso!' : 'Evento cadastrado com sucesso!';
            showMessage(message, 'success');
            
            // Voltar para lista após salvar
            setTimeout(() => {
                showEventsList();
            }, 2000);
        } else {
            showMessage(result.error || 'Erro ao salvar evento.', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão. Tente novamente.', 'error');
    }
});

// Inicialização
// document.addEventListener('DOMContentLoaded', function() {
//     // Definir data mínima como hoje
//     const today = new Date().toISOString().split('T')[0];
//     document.getElementById('datainicio').setAttribute('min', today);
//     document.getElementById('datafim').setAttribute('min', today);
//     document.getElementById('inicioinscricao').setAttribute('min', today);
//     document.getElementById('fiminscricao').setAttribute('min', today);
// });

async function openLotesModal() {
    if (editingEventId) {
        await carregarItensDoEvento(editingEventId);
    } else {
        mostrarFormularioItem();
    }
    document.getElementById('lotesModal').style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// Função para carregar itens do evento
async function carregarItensDoEvento(eventoId) {
    try {
        const response = await fetch(`/api/eventos/${eventoId}/items`);
        const itemsData = await response.json();
        
        if (response.ok && itemsData.length > 0) {
            itensDoEvento = itemsData;
            mostrarItensExistentes();
        } else {
            mostrarFormularioItem();
        }
    } catch (error) {
        console.error('Erro ao carregar itens:', error);
        mostrarFormularioItem();
    }
}


// Função super segura para abrir modal de imagens
window.abrirImagensSeguro = function() {
    console.log('=== FUNÇÃO SEGURA EXECUTADA ===');
    
    try {
        // Verificar se tudo existe
        if (typeof openModal !== 'function') {
            console.error('openModal não é uma função!');
            return;
        }
        
        console.log('Chamando openModal...');
        openModal('imagensModal');
        console.log('openModal chamada com sucesso');
        
    } catch (error) {
        console.error('ERRO na função segura:', error);
        console.error('Stack trace:', error.stack);
        
        // Tentar método alternativo
        console.log('Tentando método alternativo...');
        try {
            const modal = document.getElementById('imagensModal');
            if (modal) {
                modal.style.display = 'block';
                document.body.style.overflow = 'hidden';
                
                // Mostrar formulário
                const imageForm = document.getElementById('imageForm');
                if (imageForm) {
                    imageForm.classList.remove('hidden');
                }
                
                const imagensExistentes = document.getElementById('imagensExistentes');
                if (imagensExistentes) {
                    imagensExistentes.classList.add('hidden');
                }
                
                console.log('Modal aberto pelo método alternativo!');
            }
        } catch (error2) {
            console.error('Erro no método alternativo:', error2);
            alert('Erro crítico: ' + error2.message);
        }
    }
};


// Função para mostrar itens existentes
function mostrarItensExistentes() {
    document.getElementById('itensExistentes').classList.remove('hidden');
    document.getElementById('itemForm').classList.add('hidden');
    document.getElementById('lotesForm').classList.add('hidden');
    
    const itensLista = document.getElementById('itensLista');
    
    if (itensDoEvento.length === 0) {
        itensLista.innerHTML = '<div class="empty-state"><p>Nenhum item cadastrado</p></div>';
        return;
    }
    
    let html = '';
    itensDoEvento.forEach(item => {
        html += `
            <div class="lote-item">
                <div class="lote-header">
                    <div class="lote-title">${item.DESCRICAO} (${item.KM} KM)</div> 
                    <div class="lote-actions">
                        <button class="btn btn-primary btn-sm" onclick="gerenciarLotesDoItem(${item.IDITEM}, '${item.DESCRICAO}', ${item.KM})">Gerenciar Lotes</button>
                        <button class="btn btn-secondary btn-sm" onclick="editarItem(${item.IDITEM}, '${item.DESCRICAO}', ${item.KM})">Editar</button>  <!-- ← SEM último parâmetro -->
                        <button class="btn btn-danger btn-sm" onclick="excluirItem(${item.IDITEM})">Excluir</button>
                    </div>
                </div>
            </div>
        `;
    });
    
    itensLista.innerHTML = html;
}

// Função para mostrar formulário de item
function mostrarFormularioItem() {
    document.getElementById('itensExistentes').classList.add('hidden');
    document.getElementById('itemForm').classList.remove('hidden');
    document.getElementById('lotesForm').classList.add('hidden');
    
    document.getElementById('itemFormTitle').textContent = editandoItem ? 'Editar Item' : 'Adicionar Item';
    document.getElementById('itemFormData').reset();
    document.getElementById('editingItemId').value = '';
}

// Função para adicionar novo item
function showAddItemForm() {
    editandoItem = false;
    mostrarFormularioItem();
}

// Função para editar item
function editarItem(iditem, descricao, km, nuatletas) {
    editandoItem = true;
    mostrarFormularioItem();
    
    document.getElementById('editingItemId').value = iditem;
    document.getElementById('itemDescricao').value = descricao;
    document.getElementById('itemKm').value = km;
    document.getElementById('nuAtletas').value = nuatletas || ''; // Corrigido para usar o parâmetro diretamente
    
    console.log('Editando item:', {iditem, descricao, km, nuatletas}); // Debug
}


// FunÃ§Ã£o para salvar item
async function salvarItem() {
    const descricao = document.getElementById('itemDescricao').value;
    const km = parseFloat(document.getElementById('itemKm').value);
    const editingId = document.getElementById('editingItemId').value;
    
    if (!descricao || !km) {
        showModalMessage('Preencha todos os campos obrigatórios.', 'error');
        return;
    }
    
    const itemData = {
        descricao: descricao,
        km: km
    };
    
    try {
        let response;
        if (editingId) {
            // Editar item existente
            response = await fetch(`/api/items/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(itemData)
            });
        } else {
            // Criar novo item - CORRIGIR AQUI
            if (!editingEventId) {
                showModalMessage('Erro: ID do evento não encontrado.', 'error');
                return;
            }
            
            // ALTERAR ESTA LINHA:
            itemData.idevento = editingEventId; // Adicionar idevento aos dados
            response = await fetch('/api/items', { // Usar a rota existente
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(itemData)
            });
        }
        
        if (response.ok) {
            showModalMessage(editingId ? 'Item atualizado com sucesso!' : 'Item criado com sucesso!', 'success');
            await carregarItensDoEvento(editingEventId);
        } else {
            const error = await response.json();
            showModalMessage(error.error || 'Erro ao salvar item.', 'error');
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showModalMessage('Erro de conexão.', 'error');
    }
}

// Função para cancelar item
function cancelarItem() {
    if (editingEventId) {
        carregarItensDoEvento(editingEventId);
    } else {
        closeModal('lotesModal');
    }
}

// Função para excluir item
async function excluirItem(iditem) {
    if (confirm('Tem certeza que deseja excluir este item e todos os seus lotes?')) {
        try {
            const response = await fetch(`/api/items/${iditem}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showModalMessage('Item excluído com sucesso!', 'success');
                await carregarItensDoEvento(editingEventId);
            } else {
                showModalMessage('Erro ao excluir item.', 'error');
            }
        } catch (error) {
            showModalMessage('Erro de conexão.', 'error');
        }
    }
}


// Função para carregar itens do evento
async function carregarItensDoEvento(eventoId) {
    try {
        const response = await fetch(`/api/eventos/${eventoId}/items`);
        const itemsData = await response.json();
        
        if (response.ok && itemsData.length > 0) {
            itensDoEvento = itemsData;
            mostrarItensExistentes();
        } else {
            itensDoEvento = [];
            mostrarFormularioItem();
        }
    } catch (error) {
        console.error('Erro ao carregar itens:', error);
        itensDoEvento = [];
        mostrarFormularioItem();
    }
}

// Função para mostrar itens existentes
function mostrarItensExistentes() {
    document.getElementById('itensExistentes').classList.remove('hidden');
    document.getElementById('itemForm').classList.add('hidden');
    document.getElementById('lotesForm').classList.add('hidden');
    
    const itensLista = document.getElementById('itensLista');
    
    if (itensDoEvento.length === 0) {
        itensLista.innerHTML = '<div class="empty-state"><p>Nenhum item cadastrado</p></div>';
        return;
    }
    
    let html = '';
    itensDoEvento.forEach(item => {
        // Corrigido para passar todos os parâmetros corretos
        html += `
            <div class="lote-item">
                <div class="lote-header">
                    <div class="lote-title">${item.DESCRICAO} (${item.KM} KM)</div>
                    <div class="lote-actions">
                        <button class="btn btn-primary btn-sm" onclick="gerenciarLotesDoItem(${item.IDITEM}, '${item.DESCRICAO}', ${item.KM})">Gerenciar Lotes</button>
                        <button class="btn btn-secondary btn-sm" onclick="editarItem(${item.IDITEM}, '${item.DESCRICAO}', ${item.KM})">Editar</button>
                        <button class="btn btn-danger btn-sm" onclick="excluirItem(${item.IDITEM})">Excluir</button>
                    </div>
                </div>
            </div>
        `;
    });
    
    itensLista.innerHTML = html;
}

// Função para mostrar formulário de item
function mostrarFormularioItem() {
    document.getElementById('itensExistentes').classList.add('hidden');
    document.getElementById('itemForm').classList.remove('hidden');
    document.getElementById('lotesForm').classList.add('hidden');
    
    document.getElementById('itemFormTitle').textContent = editandoItem ? 'Editar Item' : 'Adicionar Item';
    document.getElementById('itemFormData').reset();
    document.getElementById('editingItemId').value = '';
}

// Função para adicionar novo item
function showAddItemForm() {
    editandoItem = false;
    mostrarFormularioItem();
}

// Função para editar item
function editarItem(iditem, descricao, km) {  // ← SEM nuatletas
    editandoItem = true;
    mostrarFormularioItem();
    
    document.getElementById('editingItemId').value = iditem;
    document.getElementById('itemDescricao').value = descricao;
    document.getElementById('itemKm').value = km;
}

// Função para cancelar item
function cancelarItem() {
    if (editingEventId && itensDoEvento.length > 0) {
        mostrarItensExistentes();
    } else {
        closeModal('lotesModal');
    }
}

// Função para excluir item
async function excluirItem(iditem) {
    if (confirm('Tem certeza que deseja excluir este item e todos os seus lotes?')) {
        try {
            const response = await fetch(`/api/items/${iditem}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showModalMessage('Item excluído com sucesso!', 'success');
                await carregarItensDoEvento(editingEventId);
            } else {
                const error = await response.json();
                showModalMessage(error.error || 'Erro ao excluir item.', 'error');
            }
        } catch (error) {
            showModalMessage('Erro de conexão.', 'error');
        }
    }
}

// Função para gerenciar lotes de um item
async function gerenciarLotesDoItem(iditem, descricao, km, nuatletas) {
    itemAtual = { 
        iditem, 
        descricao, 
        km, 
        nuatletas: nuatletas || 0 
    };
    await carregarLotesDoItem(iditem);
    mostrarFormularioLotes();
}

// Função para carregar lotes de um item
async function carregarLotesDoItem(iditem) {
    try {
        const response = await fetch(`/api/items/${iditem}/lotes`);
        const lotesData = await response.json();
        
        lotesDoItem = response.ok ? lotesData : [];
    } catch (error) {
        console.error('Erro ao carregar lotes do item:', error);
        lotesDoItem = [];
    }
}

// Função para mostrar formulário de lotes
function mostrarFormularioLotes() {
    document.getElementById('itensExistentes').classList.add('hidden');
    document.getElementById('itemForm').classList.add('hidden');
    document.getElementById('lotesForm').classList.remove('hidden');
    
    // Preencher info do item
    document.getElementById('lotesItemInfo').innerHTML = `
        <div class="lote-header">
            <div class="lote-title">Item: ${itemAtual.descricao} (${itemAtual.km} KM) - ${itemAtual.nuatletas || 'N/A'} atletas</div>
        </div>
    `;
    
    atualizarListaLotesDoItem();
}

// Função para atualizar lista de lotes do item
function atualizarListaLotesDoItem() {
    const lotesContainer = document.getElementById('lotesDoItem');
    
    if (lotesDoItem.length === 0) {
        lotesContainer.innerHTML = '<div class="empty-state"><p>Nenhum lote cadastrado para este item</p></div>';
        return;
    }
    
    let html = '';
    lotesDoItem.sort((a, b) => a.LOTE - b.LOTE).forEach(lote => {
        html += `
            <div class="lote-item">
                <div class="lote-header">
                    <div class="lote-title">${lote.DELOTE} - R$ ${parseFloat(lote.VLINSCRICAO || 0).toFixed(2)} - ${lote.NUATLETAS || '0'} atletas</div>  <!-- ← ADICIONAR atletas -->
                    <div class="lote-actions">
                        <button class="btn btn-primary btn-sm" onclick="editarLoteDoItem(${lote.IDLOTE})">Editar</button>
                        <button class="btn btn-danger btn-sm" onclick="excluirLoteDoItem(${lote.IDLOTE})">Excluir</button>
                    </div>
                </div>
                <div class="lote-details">
                    <div class="lote-detail"><strong>Lote:</strong> ${lote.LOTE}</div>
                    <div class="lote-detail"><strong>Atletas:</strong> ${lote.NUATLETAS || '0'}</div>  <!-- ← ADICIONAR esta linha -->
                    <div class="lote-detail"><strong>Valor:</strong> R$ ${parseFloat(lote.VLINSCRICAO || 0).toFixed(2)}</div>
                    <div class="lote-detail"><strong>Taxa:</strong> ${lote.PCTAXA}%</div>
                    <div class="lote-detail"><strong>Início:</strong> ${formatDate(lote.DTINICIO)}</div>
                    <div class="lote-detail"><strong>Fim:</strong> ${formatDate(lote.DTFIM)}</div>
                    <div class="lote-detail"><strong>Nº Atletas:</strong> ${parseInt(lote.NUATLETAS || '0')}</div>
                </div>
            </div>
        `;
    });
    
    lotesContainer.innerHTML = html;
}

// Função para voltar para lista de itens
function voltarParaItens() {
    mostrarItensExistentes();
}

// Função para adicionar lote para item
function adicionarLoteParaItem() {
    editandoLote = false;
    document.getElementById('loteFormContainer').classList.remove('hidden');
    document.getElementById('editingLoteId').value = '';
    limparFormularioLote();
}


// Funções auxiliares para lotes
function calcularTaxaLote() {
    const valorInput = document.getElementById('loteVlinscricao');
    const taxaInput = document.getElementById('lotePctaxa');
    
    const valor = parseFloat(valorInput.value) || 0;
    let taxa = 0;
    
    if (valor <= 100) taxa = 10;
    else if (valor <= 150) taxa = 9;
    else if (valor <= 200) taxa = 8;
    else taxa = 7;
    
    taxaInput.value = taxa;
}

function atualizarDescricaoLoteAtual() {
    const loteInput = document.getElementById('loteLote');
    const deloteInput = document.getElementById('loteDelote');
    
    const numeroLote = parseInt(loteInput.value);
    if (numeroLote) {
        deloteInput.value = `${numeroLote}º LOTE`;
    }
}

function limparFormularioLote() {
    document.getElementById('loteVlinscricao').value = '';
    document.getElementById('lotePctaxa').value = '';
    document.getElementById('loteDtinicio').value = '';
    document.getElementById('loteDtfim').value = '';
    document.getElementById('loteLote').value = '';
    document.getElementById('loteDelote').value = '';
}


//////////////////////////////

// Função para gerenciar lotes de um item
async function gerenciarLotesDoItem(iditem, descricao, km) {
    // Buscar o item completo para pegar o nuatletas
    const item = itensDoEvento.find(i => i.IDITEM == iditem);
    itemAtual = { 
        iditem, 
        descricao, 
        km, 
        nuatletas: item ? item.NUATLETAS : 0 
    };
    await carregarLotesDoItem(iditem);
    mostrarFormularioLotes();
}

// Função para carregar lotes de um item
async function carregarLotesDoItem(iditem) {
    try {
        const response = await fetch(`/api/items/${iditem}/lotes`);
        const lotesData = await response.json();
        
        lotesDoItem = response.ok ? lotesData : [];
    } catch (error) {
        console.error('Erro ao carregar lotes do item:', error);
        lotesDoItem = [];
    }
}

// Função para mostrar formulário de lotes
function mostrarFormularioLotes() {
    document.getElementById('itensExistentes').classList.add('hidden');
    document.getElementById('itemForm').classList.add('hidden');
    document.getElementById('lotesForm').classList.remove('hidden');
    
    // Preencher info do item
    document.getElementById('lotesItemInfo').innerHTML = `
        <div class="lote-header">
            <div class="lote-title">Item: ${itemAtual.descricao} (${itemAtual.km} KM)</div>
        </div>
    `;
    
    atualizarListaLotesDoItem();
}

// Função para atualizar lista de lotes do item
function atualizarListaLotesDoItem() {
    const lotesContainer = document.getElementById('lotesDoItem');
    
    if (lotesDoItem.length === 0) {
        lotesContainer.innerHTML = '<div class="empty-state"><p>Nenhum lote cadastrado para este item</p></div>';
        return;
    }
    
    let html = '';
    lotesDoItem.sort((a, b) => a.LOTE - b.LOTE).forEach(lote => {
        html += `
            <div class="lote-item">
                <div class="lote-header">
                    <div class="lote-title">${lote.DELOTE} - R$ ${parseFloat(lote.VLINSCRICAO || 0).toFixed(2)}</div>
                    <div class="lote-actions">
                        <button class="btn btn-primary btn-sm" onclick="editarLoteDoItem(${lote.IDLOTE})">Editar</button>
                        <button class="btn btn-danger btn-sm" onclick="excluirLoteDoItem(${lote.IDLOTE})">Excluir</button>
                    </div>
                </div>
                <div class="lote-details">
                    <div class="lote-detail"><strong>Lote:</strong> ${lote.LOTE}</div>
                    <div class="lote-detail"><strong>Valor:</strong> R$ ${parseFloat(lote.VLINSCRICAO || 0).toFixed(2)}</div>
                    <div class="lote-detail"><strong>Taxa:</strong> ${lote.PCTAXA}%</div>
                    <div class="lote-detail"><strong>Início:</strong> ${formatDate(lote.DTINICIO)}</div>
                    <div class="lote-detail"><strong>Fim:</strong> ${formatDate(lote.DTFIM)}</div>
                    <div class="lote-detail"><strong>Nº Atletas:</strong> ${parseInt(lote.NUATLETAS || '0')}</div>
                </div>
            </div>
        `;
    });
    
    lotesContainer.innerHTML = html;
}

// Função para voltar para lista de itens
function voltarParaItens() {
    mostrarItensExistentes();
}

// Função para adicionar lote para item
function adicionarLoteParaItem() {
    editandoLote = false;
    document.getElementById('loteFormContainer').classList.remove('hidden');
    document.getElementById('editingLoteId').value = '';
    limparFormularioLote();
}

// Função para editar lote do item
async function editarLoteDoItem(idlote) {
    editandoLote = true;
    const lote = lotesDoItem.find(l => l.IDLOTE == idlote);
    
    if (!lote) return;
    
    document.getElementById('loteFormContainer').classList.remove('hidden');
    document.getElementById('editingLoteId').value = idlote;
    
    document.getElementById('loteVlinscricao').value = lote.VLINSCRICAO;
    document.getElementById('lotePctaxa').value = lote.PCTAXA;
    document.getElementById('loteNuatletas').value = lote.NUATLETAS || '';  // ← DESCOMENTAR E CORRIGIR
    document.getElementById('loteDtinicio').value = lote.DTINICIO;
    document.getElementById('loteDtfim').value = lote.DTFIM;
    document.getElementById('loteLote').value = lote.LOTE;
    document.getElementById('loteDelote').value = lote.DELOTE;
}

// Função para salvar lote
async function salvarLote() {
    const vlinscricao = parseFloat(document.getElementById('loteVlinscricao').value);
    const pctaxa = parseFloat(document.getElementById('lotePctaxa').value);
    const nuatletas = parseInt(document.getElementById('loteNuatletas').value);  // ← ADICIONAR
    const dtinicio = document.getElementById('loteDtinicio').value || null;
    const dtfim = document.getElementById('loteDtfim').value || null;
    const lote = parseInt(document.getElementById('loteLote').value);
    const delote = document.getElementById('loteDelote').value;
    const editingId = document.getElementById('editingLoteId').value;
    
    if (!vlinscricao || !lote || !nuatletas) {  // ← ADICIONAR nuatletas na validação
        showModalMessage('Preencha todos os campos obrigatórios.', 'error');
        return;
    }
    
    const loteData = {
        iditem: itemAtual.iditem,
        idevento: editingEventId,
        vlinscricao: vlinscricao,
        pctaxa: pctaxa,
        nuatletas: nuatletas,  // ← ADICIONAR
        dtinicio: dtinicio,
        dtfim: dtfim,
        lote: lote,
        delote: delote
    };
    
    try {
        let response;
        if (editingId) {
            // Editar lote existente
            response = await fetch(`/api/lotes/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(loteData)
            });
        } else {
            // Criar novo lote
            response = await fetch('/api/lotes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(loteData)
            });
        }
        
        if (response.ok) {
            showModalMessage(editingId ? 'Lote atualizado com sucesso!' : 'Lote criado com sucesso!', 'success');
            await carregarLotesDoItem(itemAtual.iditem);
            atualizarListaLotesDoItem();
            document.getElementById('loteFormContainer').classList.add('hidden');
        } else {
            const error = await response.json();
            showModalMessage(error.error || 'Erro ao salvar lote.', 'error');
        }
    } catch (error) {
        showModalMessage('Erro de conexão.', 'error');
    }
}

// Função para cancelar lote
function cancelarLote() {
    document.getElementById('loteFormContainer').classList.add('hidden');
}

// Função para excluir lote do item
async function excluirLoteDoItem(idlote) {
    if (confirm('Tem certeza que deseja excluir este lote?')) {
        try {
            const response = await fetch(`/api/lotes/${idlote}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showModalMessage('Lote excluído com sucesso!', 'success');
                await carregarLotesDoItem(itemAtual.iditem);
                atualizarListaLotesDoItem();
            } else {
                showModalMessage('Erro ao excluir lote.', 'error');
            }
        } catch (error) {
            showModalMessage('Erro de conexão.', 'error');
        }
    }
}

// Funções auxiliares para lotes
function calcularTaxaLote() {
    const valorInput = document.getElementById('loteVlinscricao');
    const taxaInput = document.getElementById('lotePctaxa');
    
    const valor = parseFloat(valorInput.value) || 0;
    let taxa = 0;
    
    if (valor <= 100) taxa = 10;
    else if (valor <= 150) taxa = 9;
    else if (valor <= 200) taxa = 8;
    else taxa = 7;
    
    taxaInput.value = taxa;
}

function atualizarDescricaoLoteAtual() {
    const loteInput = document.getElementById('loteLote');
    const deloteInput = document.getElementById('loteDelote');
    
    const numeroLote = parseInt(loteInput.value);
    if (numeroLote) {
        deloteInput.value = `${numeroLote}º LOTE`;
    }
}

function limparFormularioLote() {
    document.getElementById('loteVlinscricao').value = '';
    document.getElementById('lotePctaxa').value = '';
    document.getElementById('loteDtinicio').value = '';
    document.getElementById('loteDtfim').value = '';
    document.getElementById('loteNuatletas').value = '';
    document.getElementById('loteLote').value = '';
    document.getElementById('loteDelote').value = '';
}        



////////////////////////////////


// Função para carregar lotes existentes
async function carregarLotes(eventoId) {
    try {
        console.log('Carregando lotes para evento:', eventoId); // Debug
        const response = await fetch(`/api/eventos/${eventoId}/lotes`);
        const lotesData = await response.json();
        
        console.log('Resposta da API:', lotesData); // Debug
        console.log('Response OK:', response.ok); // Debug
        console.log('Quantidade de lotes:', lotesData.length); // Debug
        
        if (response.ok && lotesData.length > 0) {
            lotes = lotesData;
            console.log('Lotes carregados:', lotes); // Debug
            mostrarLotesExistentes();
        } else {
            console.log('Nenhum lote encontrado ou erro na resposta'); // Debug
            mostrarFormularioLotes();
        }
    } catch (error) {
        console.error('Erro ao carregar lotes:', error);
        mostrarFormularioLotes();
    }
}


// Função auxiliar para formatação de data
function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        // Se já está no formato YYYY-MM-DD, usar diretamente
        let date;
        if (dateString.includes('-')) {
            const parts = dateString.split('T')[0]; // Remove a parte do tempo se existir
            date = new Date(parts + 'T12:00:00'); // Adiciona meio-dia para evitar problemas de timezone
        } else {
            date = new Date(dateString);
        }
        
        if (isNaN(date.getTime())) {
            return '-';
        }
        
        return date.toLocaleDateString('pt-BR');
    } catch (error) {
        console.error('Erro ao formatar data:', error, dateString);
        return '-';
    }
}

function openModal(modalId) {
    console.log('=== openModal INICIADA ===');
    console.log('Parâmetro modalId:', modalId, typeof modalId);
    
    try {
        // Verificações básicas
        if (!modalId) {
            throw new Error('modalId é obrigatório');
        }
        
        if (typeof modalId !== 'string') {
            throw new Error('modalId deve ser string');
        }
        
        console.log('Verificações básicas OK');
        
        // Verificar qual modal abrir
        if (modalId === 'imagensModal') {
            console.log('Detectado: modal de imagens');
            
            // Verificar se a função existe
            if (typeof openImagensModal !== 'function') {
                throw new Error('openImagensModal não é uma função');
            }
            
            console.log('Chamando openImagensModal...');
            openImagensModal();
            console.log('openImagensModal executada');
            return;
        }
        
        if (modalId === 'lotesModal') {
            console.log('Detectado: modal de lotes');
            if (typeof openLotesModal === 'function') {
                openLotesModal();
            } else {
                console.error('openLotesModal não existe');
            }
            return;
        }
        
        // Modal padrão
        console.log('Abrindo modal padrão:', modalId);
        const modal = document.getElementById(modalId);
        
        if (!modal) {
            throw new Error('Modal não encontrado: ' + modalId);
        }
        
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        console.log('Modal padrão aberto com sucesso');
        
    } catch (error) {
        console.error('=== ERRO EM OPENMODAL ===');
        console.error('Erro:', error.message);
        console.error('Stack:', error.stack);
        console.error('modalId recebido:', modalId);
        
        // Mostrar erro para o usuário
        alert('Erro ao abrir modal: ' + error.message);
        
        // Re-throw para não mascarar o erro
        throw error;
    }
}       

// Função para lidar com o upload do banner
function handleBannerUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    console.log('Arquivo selecionado:', file.name, 'Tipo:', file.type, 'Tamanho:', file.size); // Debug
    
    // Validar tipo de arquivo
    if (!file.type.startsWith('image/')) {
        showModalMessage('Por favor, selecione apenas arquivos de imagem.', 'error');
        event.target.value = '';
        return;
    }
    
    // Validar tamanho (máximo 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showModalMessage('A imagem deve ter no máximo 5MB.', 'error');
        event.target.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        bannerData = e.target.result;
        
        console.log('Banner carregado:', bannerData.substring(0, 50) + '...'); // Debug
        
        // Mostrar preview
        document.getElementById('bannerImage').src = e.target.result;
        document.getElementById('bannerPreview').style.display = 'block';
        
        // Atualizar o botão do input file
        updateFileInputLabel();
        
        showModalMessage('Imagem carregada com sucesso!', 'success');
    };
    reader.readAsDataURL(file);
}

// Função para atualizar o label do input de arquivo
function updateFileInputLabel() {
    const fileInput = document.getElementById('bannerFile');
    const hasImage = bannerData || document.getElementById('bannerPreview').style.display === 'block';
    
    if (hasImage) {
        // Criar um wrapper se não existir
        let wrapper = fileInput.parentElement.querySelector('.file-input-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'file-input-wrapper';
            wrapper.style.position = 'relative';
            fileInput.parentElement.insertBefore(wrapper, fileInput);
            wrapper.appendChild(fileInput);
        }
        
        // Adicionar overlay com texto personalizado
        let overlay = wrapper.querySelector('.file-input-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'file-input-overlay';
            overlay.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                display: flex;
                align-items: center;
                padding: 12px;
                cursor: pointer;
                pointer-events: none;
                font-size: 16px;
                color: #666;
            `;
            wrapper.appendChild(overlay);
        }
        
        overlay.innerHTML = `
            <button type="button" style="
                background: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 500;
                margin-right: 10px;
                pointer-events: none;
            ">Alterar arquivo</button>
            <span style="color: #666;">Imagem selecionada</span>
        `;
        
        // Tornar o input transparente
        fileInput.style.opacity = '0';
    }
}

// Função para remover banner
function removeBanner() {
    bannerData = null;
    const fileInput = document.getElementById('bannerFile');
    fileInput.value = '';
    document.getElementById('bannerPreview').style.display = 'none';
    document.getElementById('bannerImage').src = '';
    
    // Restaurar o input file ao estado original
    const wrapper = fileInput.parentElement.querySelector('.file-input-wrapper');
    if (wrapper) {
        const overlay = wrapper.querySelector('.file-input-overlay');
        if (overlay) {
            overlay.remove();
        }
        fileInput.style.opacity = '1';
        wrapper.parentElement.insertBefore(fileInput, wrapper);
        wrapper.remove();
    }
}

// Função para mostrar mensagens modais
function showModalMessage(message, type) {
    const modal = document.getElementById('messageModal');
    const icon = document.getElementById('messageIcon');
    const iconText = document.getElementById('messageIconText');
    const title = document.getElementById('messageTitle');
    const text = document.getElementById('messageText');
    const button = document.getElementById('messageButton');
    
    // Configurar conteúdo baseado no tipo
    if (type === 'success') {
        icon.className = 'message-modal-icon success';
        iconText.textContent = '✓';
        title.textContent = 'Sucesso';
        button.className = 'message-modal-button success';
    } else if (type === 'error') {
        icon.className = 'message-modal-icon error';
        iconText.textContent = '✕';
        title.textContent = 'Erro';
        button.className = 'message-modal-button error';
    }
    
    text.textContent = message;
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// Função para fechar modal de mensagem
function closeMessageModal() {
    const modal = document.getElementById('messageModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Manter função showMessage para compatibilidade (redirecionando para modal)
function showMessage(message, type) {
    showModalMessage(message, type);
}

// Fechar modal ao clicar fora
document.addEventListener('click', function(event) {
    const modal = document.getElementById('messageModal');
    if (event.target === modal) {
        closeMessageModal();
    }
});

// ===== FUNÇÕES PARA GERENCIAMENTO DE IMAGENS =====

// Função para abrir modal de imagens
async function openImagensModal() {
    console.log('Abrindo modal de imagens...');
    
    // Abrir o modal
    const modal = document.getElementById('imagensModal');
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Reset das variáveis
    imagensDoEvento = [];
    editandoImagem = false;
    
    if (editingEventId) {
        // Carregar imagens existentes
        await carregarImagensDoEvento(editingEventId);
        
        if (imagensDoEvento.length > 0) {
            mostrarListaImagens(); // Nova função - mostra lista como "Meus Eventos"
        } else {
            mostrarFormularioImagem();
        }
    } else {
        mostrarFormularioImagem();
    }
}

function mostrarListaImagens() {
    // Esconder outros elementos
    document.getElementById('imagensExistentes').classList.add('hidden');
    document.getElementById('imageForm').classList.add('hidden');
    
    // Criar estrutura igual aos eventos
    const imagensContent = document.getElementById('imagensContent');
    imagensContent.innerHTML = `
        <div class="events-list">
            <div class="events-header">
                <h3>Imagens do Evento</h3>
                <button type="button" class="btn btn-success" onclick="adicionarNovaImagem()">
                    + Adicionar Imagem
                </button>
            </div>
            <div id="imagensListaSimples">
                ${imagensDoEvento.length === 0 ? 
                    '<div class="empty-state"><h4>Nenhuma imagem encontrada</h4><p>Clique em "Adicionar Imagem" para criar a primeira imagem</p></div>' :
                    imagensDoEvento.map(imagem => `
                        <div class="event-item">
                            <div class="event-info">
                                <div class="event-title">${imagem.TITULO_IMG}</div>
                                <div class="event-details">ID: ${imagem.ID}</div>
                            </div>
                            <div class="event-actions">
                                <button type="button" class="btn btn-primary btn-sm" onclick="editarImagemDaLista(${imagem.ID}, '${imagem.TITULO_IMG.replace(/'/g, "\\'")}')">
                                    Editar
                                </button>
                                <button type="button" class="btn btn-danger btn-sm" onclick="excluirImagemDaLista(${imagem.ID})">
                                    Excluir
                                </button>
                            </div>
                        </div>
                    `).join('')
                }
            </div>
        </div>
    `;
}

function adicionarNovaImagem() {
    editandoImagem = false;
    mostrarFormularioImagem();
}

function editarImagemDaLista(id, titulo) {
    editandoImagem = true;
    imagemAtual = { id, titulo };
    mostrarFormularioImagem();
    
    // Preencher dados no formulário
    document.getElementById('editingImageId').value = id;
    document.getElementById('imageTitulo').value = titulo;
    
    // Arquivo não é obrigatório na edição
    const fileInput = document.getElementById('imageFile');
    fileInput.required = false;
}

async function excluirImagemDaLista(id) {
    if (confirm('Tem certeza que deseja excluir esta imagem?')) {
        try {
            const response = await fetch(`/api/evento-imagens/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showModalMessage('Imagem excluída com sucesso!', 'success');
                // Recarregar a lista
                await carregarImagensDoEvento(editingEventId);
                mostrarListaImagens();
            } else {
                const error = await response.json();
                showModalMessage(error.error || 'Erro ao excluir imagem.', 'error');
            }
        } catch (error) {
            showModalMessage('Erro de conexão.', 'error');
        }
    }
}


// Função para carregar imagens do evento
async function carregarImagensDoEvento(eventoId) {
    try {
        console.log('Fazendo requisição para:', `/api/eventos/${eventoId}/imagens`);
        const response = await fetch(`/api/eventos/${eventoId}/imagens`);
        
        console.log('Status da resposta:', response.status);
        
        if (response.ok) {
            const imagensData = await response.json();
            console.log('Dados recebidos:', imagensData);
            
            if (imagensData && imagensData.length > 0) {
                imagensDoEvento = imagensData;
                mostrarImagensExistentes();
            } else {
                console.log('Nenhuma imagem encontrada');
                imagensDoEvento = [];
                mostrarFormularioImagem();
            }
        } else {
            console.log('Erro na resposta:', response.status);
            imagensDoEvento = [];
            mostrarFormularioImagem();
        }
    } catch (error) {
        console.error('Erro ao carregar imagens:', error);
        imagensDoEvento = [];
        mostrarFormularioImagem();
    }
}

// Função para mostrar imagens existentes
function mostrarImagensExistentes() {
    console.log('=== mostrarImagensExistentes ===');
    console.log('imagensDoEvento:', imagensDoEvento);
    
    const imagensExistentes = document.getElementById('imagensExistentes');
    const imageForm = document.getElementById('imageForm');
    const imagensLista = document.getElementById('imagensLista');
    
    if (!imagensExistentes || !imageForm || !imagensLista) {
        console.error('Elementos não encontrados:', {
            imagensExistentes: !!imagensExistentes,
            imageForm: !!imageForm,
            imagensLista: !!imagensLista
        });
        return;
    }
    
    console.log('Mostrando seção de imagens existentes');
    imagensExistentes.classList.remove('hidden');
    imageForm.classList.add('hidden');
    
    if (imagensDoEvento.length === 0) {
        imagensLista.innerHTML = '<div class="empty-state"><p>Nenhuma imagem cadastrada</p></div>';
        console.log('Exibindo estado vazio');
        return;
    }
    
    let html = '';
    imagensDoEvento.forEach((imagem, index) => {
        console.log(`Processando imagem ${index}:`, imagem);
        try {
            const imagemSrc = `data:image/jpeg;base64,${imagem.IMG}`;
            html += `
                <div class="lote-item">
                    <div class="lote-header">
                        <div class="lote-title">${imagem.TITULO_IMG}</div>
                        <div class="lote-actions">
                            <button class="btn btn-primary btn-sm" onclick="editarImagem(${imagem.ID}, '${imagem.TITULO_IMG.replace(/'/g, "\\'")}')">Editar</button>
                            <button class="btn btn-danger btn-sm" onclick="excluirImagem(${imagem.ID})">Excluir</button>
                        </div>
                    </div>
                    <div class="lote-details">
                        <img src="${imagemSrc}" alt="${imagem.TITULO_IMG}" style="max-width: 100%; max-height: 200px; border-radius: 8px; margin-top: 10px;">
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Erro ao processar imagem:', error, imagem);
        }
    });
    
    imagensLista.innerHTML = html;
    console.log('HTML final das imagens:', html.length, 'caracteres');
}

// Função para mostrar formulário de imagem
function mostrarFormularioImagem() {
    const imagensContent = document.getElementById('imagensContent');
    imagensContent.innerHTML = `
        <div class="back-btn">
            <button type="button" class="btn btn-secondary" onclick="voltarParaListaImagens()">
                ← Voltar para Lista
            </button>
        </div>
        
        <form id="imageFormData">
            <h3 id="imageFormTitle">${editandoImagem ? 'Editar Imagem' : 'Adicionar Imagem'}</h3>
            <input type="hidden" id="editingImageId" value="${editandoImagem && imagemAtual ? imagemAtual.id : ''}">
            
            <div class="form-group">
                <label for="imageTitulo">Título da Imagem *</label>
                <input type="text" id="imageTitulo" maxlength="45" required placeholder="Ex: Vista aérea da largada" 
                    value="${editandoImagem && imagemAtual ? imagemAtual.titulo : ''}">
            </div>
            
            <div class="form-group">
                <label for="imageFile">Arquivo da Imagem ${editandoImagem ? '' : '*'}</label>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <input type="file" id="imageFile" accept="image/*" onchange="handleImageUpload(event)" ${editandoImagem ? '' : 'required'}>
                    <div id="imagePreview" style="display: none;">
                        <img id="imagePreviewImg" src="" alt="Preview da imagem" style="max-height: 200px; width: 100%; object-fit: contain; border: 2px solid #ddd; border-radius: 8px;">
                        <button type="button" class="btn btn-danger btn-sm" onclick="removeImagePreview()" style="margin-top: 10px;">Remover Imagem</button>
                    </div>
                </div>
            </div>
            
            <div class="form-actions">
                <button type="button" class="btn btn-success" onclick="salvarImagem()">Salvar Imagem</button>
                <button type="button" class="btn btn-secondary" onclick="voltarParaListaImagens()">Cancelar</button>
            </div>
        </form>
    `;
}

function voltarParaListaImagens() {
    if (imagensDoEvento.length > 0) {
        mostrarListaImagens();
    } else {
        closeModal('imagensModal');
    }
}

// Função para adicionar nova imagem
function showAddImageForm() {
    editandoImagem = false;
    mostrarFormularioImagem();
}

// Função para editar imagem
function editarImagem(id, titulo) {
    editandoImagem = true;
    mostrarFormularioImagem();
    
    document.getElementById('editingImageId').value = id;
    document.getElementById('imageTitulo').value = titulo;
    
    // Para edição, não precisamos mostrar a imagem atual no preview
    // mas podemos remover a obrigatoriedade do arquivo
    const fileInput = document.getElementById('imageFile');
    fileInput.required = false;
}

// Função para lidar com upload de imagem
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validar tipo de arquivo
    if (!file.type.startsWith('image/')) {
        showModalMessage('Por favor, selecione apenas arquivos de imagem.', 'error');
        event.target.value = '';
        return;
    }
    
    // Validar tamanho (máximo 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showModalMessage('A imagem deve ter no máximo 5MB.', 'error');
        event.target.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        imagemData = e.target.result;
        
        // Mostrar preview
        document.getElementById('imagePreviewImg').src = e.target.result;
        document.getElementById('imagePreview').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

// Função para remover preview da imagem
function removeImagePreview() {
    imagemData = null;
    const fileInput = document.getElementById('imageFile');
    fileInput.value = '';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('imagePreviewImg').src = '';
}

// Função para salvar imagem
async function salvarImagem() {
    const titulo = document.getElementById('imageTitulo').value;
    const editingId = document.getElementById('editingImageId').value;
    
    if (!titulo) {
        showModalMessage('Preencha o título da imagem.', 'error');
        return;
    }
    
    if (!editingId && !imagemData) {
        showModalMessage('Selecione uma imagem.', 'error');
        return;
    }
    
    const imagemDataObj = {
        idevento: editingEventId,
        titulo_img: titulo
    };
    
    if (imagemData) {
        imagemDataObj.img = imagemData;
    }
    
    try {
        let response;
        if (editingId) {
            response = await fetch(`/api/evento-imagens/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(imagemDataObj)
            });
        } else {
            response = await fetch('/api/evento-imagens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(imagemDataObj)
            });
        }
        
        if (response.ok) {
            showModalMessage(editingId ? 'Imagem atualizada com sucesso!' : 'Imagem adicionada com sucesso!', 'success');
            
            // Recarregar e mostrar lista
            await carregarImagensDoEvento(editingEventId);
            setTimeout(() => {
                mostrarListaImagens();
            }, 1500);
        } else {
            const error = await response.json();
            showModalMessage(error.error || 'Erro ao salvar imagem.', 'error');
        }
    } catch (error) {
        showModalMessage('Erro de conexão.', 'error');
    }
}

// Função para cancelar imagem
function cancelarImagem() {
    if (editingEventId && imagensDoEvento.length > 0) {
        mostrarImagensExistentes();
    } else {
        closeModal('imagensModal');
    }
}

// Função para excluir imagem
async function excluirImagem(id) {
    if (confirm('Tem certeza que deseja excluir esta imagem?')) {
        try {
            const response = await fetch(`/api/evento-imagens/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showModalMessage('Imagem excluída com sucesso!', 'success');
                await carregarImagensDoEvento(editingEventId);
            } else {
                const error = await response.json();
                showModalMessage(error.error || 'Erro ao excluir imagem.', 'error');
            }
        } catch (error) {
            showModalMessage('Erro de conexão.', 'error');
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        console.log('=== VERIFICANDO ELEMENTOS ===');
        console.log('imagensModal:', document.getElementById('imagensModal'));
        console.log('imagensExistentes:', document.getElementById('imagensExistentes'));
        console.log('imageForm:', document.getElementById('imageForm'));
        console.log('imagensLista:', document.getElementById('imagensLista'));
        
        // Encontrar o botão
        const botoes = document.querySelectorAll('button');
        console.log('Total de botões:', botoes.length);
        
        botoes.forEach((btn, index) => {
            if (btn.textContent.includes('Imagens do Evento')) {
                console.log(`Botão ${index} encontrado:`, btn);
                console.log('onclick:', btn.getAttribute('onclick'));
            }
        });
    }, 1000);
});

