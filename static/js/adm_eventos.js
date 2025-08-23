// Variáveis globais
let inscricoesList = [];
let selectedIds = new Set();

// Autenticação
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
            loadInscricoes(); // Carregar automaticamente após login
        } else {
            showMessage('Senha incorreta!', 'error');
        }
    } catch (error) {
        showMessage('Erro de conexão. Tente novamente.', 'error');
    }
});

// Logout
function logout() {
    document.getElementById('authScreen').classList.remove('hidden');
    document.getElementById('mainScreen').classList.add('hidden');
    document.getElementById('senha').value = '';
    selectedIds.clear();
    updateTotals();
}

// Carregar inscrições
async function loadInscricoes() {
    const mostrarEnviados = document.getElementById('filtroEnviado').checked;
    
    try {
        const flVlEnviado = mostrarEnviados ? 'S' : 'N';
        const response = await fetch(`/api/inscricoes?fl_vlenviado=${flVlEnviado}`);
        const inscricoes = await response.json();

        inscricoesList = inscricoes;
        selectedIds.clear();
        renderInscricoes();
        updateTotals();
        
        // Atualizar título
        const title = mostrarEnviados ? 'Inscrições com Valores Enviados' : 'Inscrições Pendentes';
        document.getElementById('inscricoesTitle').textContent = title;
        
        // Mostrar footer sempre que houver inscrições
        if (inscricoes.length > 0) {
            document.getElementById('footerTotais').classList.remove('hidden');
        } else {
            document.getElementById('footerTotais').classList.add('hidden');
        }

    } catch (error) {
        showMessage('Erro ao carregar inscrições.', 'error');
    }
}

// Renderizar lista de inscrições
function renderInscricoes() {
    const content = document.getElementById('inscricoesContent');
    
    if (inscricoesList.length === 0) {
        const mostrarEnviados = document.getElementById('filtroEnviado').checked;
        const emptyMessage = mostrarEnviados ? 
            'Nenhuma inscrição com valor enviado' : 
            'Nenhuma inscrição pendente de envio';
            
        content.innerHTML = `
            <div class="empty-state">
                <h4>${emptyMessage}</h4>
                <p>Não há registros para exibir no momento</p>
            </div>
        `;
        return;
    }

    const mostrarEnviados = document.getElementById('filtroEnviado').checked;
    
    let html = `
        <div class="table-container">
            <table class="inscricoes-table">
                <thead>
                    <tr>
                        ${!mostrarEnviados ? '<th>Selecionar</th>' : ''}
                        <th>ID</th>
                        <th>Modalidade</th>
                        <th>Nome Completo</th>
                        <th>Idade</th>
                        <th>Sexo</th>
                        <th>Data Pagamento</th>
                        <th>Vl. Inscrição</th>
                        <th>Vl. Pago</th>
                        <th>Vl. Líquido</th>
                        <th>Vl. Crédito</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;

    inscricoesList.forEach(inscricao => {
        const isSelected = selectedIds.has(inscricao.IDINSCRICAO);
        const rowClass = isSelected ? 'selected' : '';
        
        html += `
            <tr class="${rowClass}">
                ${!mostrarEnviados ? `
                <td>
                    <input type="checkbox" 
                            class="select-checkbox" 
                            ${isSelected ? 'checked' : ''}
                            onchange="toggleSelection(${inscricao.IDINSCRICAO})">
                </td>
                ` : ''}
                <td>${inscricao.IDINSCRICAO}</td>
                <td>${inscricao.MODALIDADE}</td>
                <td>${inscricao.NOME_COMPLETO}</td>
                <td>${inscricao.IDADE}</td>
                <td>${inscricao.SEXO}</td>
                <td>${formatDate(inscricao.DTPAGAMENTO)}</td>
                <td class="valor-cell">R$ ${inscricao.VLINSCRICAO.toFixed(2)}</td>
                <td class="valor-cell">R$ ${inscricao.VLPAGO.toFixed(2)}</td>
                <td class="valor-cell">R$ ${inscricao.VLLIQUIDO.toFixed(2)}</td>
                <td class="valor-cell">R$ ${inscricao.VLCREDITO.toFixed(2)}</td>
                <td>
                    <span class="status-badge ${inscricao.FL_VLENVIADO === 'S' ? 'status-enviado' : 'status-pendente'}">
                        ${inscricao.FL_VLENVIADO === 'S' ? 'Enviado' : 'Pendente'}
                    </span>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    content.innerHTML = html;
}

// Toggle seleção de item
function toggleSelection(id) {
    if (selectedIds.has(id)) {
        selectedIds.delete(id);
    } else {
        selectedIds.add(id);
    }
    
    updateTotals();
    renderInscricoes(); // Re-renderizar para atualizar classes CSS
}

// Atualizar totais
function updateTotals() {
    let totalInscricao = 0;
    let totalPago = 0;
    let totalLiquido = 0;
    let totalCredito = 0;

    const mostrarEnviados = document.getElementById('filtroEnviado').checked;

    if (mostrarEnviados) {
        // Para valores enviados, calcular total de todas as inscrições visíveis
        inscricoesList.forEach(inscricao => {
            totalInscricao += inscricao.VLINSCRICAO;
            totalPago += inscricao.VLPAGO;
            totalLiquido += inscricao.VLLIQUIDO;
            totalCredito += inscricao.VLCREDITO;
        });
    } else {
        // Para pendentes, calcular apenas os selecionados
        selectedIds.forEach(id => {
            const inscricao = inscricoesList.find(i => i.IDINSCRICAO === id);
            if (inscricao) {
                totalInscricao += inscricao.VLINSCRICAO;
                totalPago += inscricao.VLPAGO;
                totalLiquido += inscricao.VLLIQUIDO;
                totalCredito += inscricao.VLCREDITO;
            }
        });
    }

    document.getElementById('totalInscricao').textContent = `R$ ${totalInscricao.toFixed(2)}`;
    document.getElementById('totalPago').textContent = `R$ ${totalPago.toFixed(2)}`;
    document.getElementById('totalLiquido').textContent = `R$ ${totalLiquido.toFixed(2)}`;
    document.getElementById('totalCredito').textContent = `R$ ${totalCredito.toFixed(2)}`;

    // Atualizar botão e estilo conforme o modo
    const confirmarBtn = document.getElementById('confirmarBtn');
    const confirmarBtnText = document.getElementById('confirmarBtnText');
    
    if (mostrarEnviados) {
        confirmarBtn.classList.add('enviados');
        confirmarBtn.disabled = false;
        confirmarBtnText.textContent = 'Total de Valores Enviados';
    } else {
        confirmarBtn.classList.remove('enviados');
        confirmarBtn.disabled = selectedIds.size === 0;
        confirmarBtnText.textContent = 'Confirmar Envio do Valor';
    }
}

// Confirmar envio
async function confirmarEnvio() {
    const mostrarEnviados = document.getElementById('filtroEnviado').checked;
    
    // Se está visualizando enviados, não faz nada (botão apenas informativo)
    if (mostrarEnviados) {
        return;
    }

    if (selectedIds.size === 0) {
        showMessage('Selecione pelo menos uma inscrição.', 'error');
        return;
    }

    if (!confirm(`Confirmar o envio de valores para ${selectedIds.size} inscrição(ões)?`)) {
        return;
    }

    try {
        const idsArray = Array.from(selectedIds);
        
        const response = await fetch('/api/inscricoes/confirmar-envio', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ids: idsArray
            })
        });

        const result = await response.json();

        if (response.ok) {
            showMessage(`Valores enviados com sucesso para ${selectedIds.size} inscrição(ões)!`, 'success');
            
            // Recarregar lista
            selectedIds.clear();
            await loadInscricoes();
        } else {
            showMessage(result.error || 'Erro ao confirmar envio.', 'error');
        }
        
    } catch (error) {
        showMessage('Erro ao confirmar envio.', 'error');
    }
}

// Utilitários
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function showMessage(message, type) {
    const messagesDiv = document.getElementById('messages');
    const messageClass = type === 'success' ? 'message-success' : 'message-error';
    messagesDiv.innerHTML = `<div class="message ${messageClass}">${message}</div>`;
    
    setTimeout(() => {
        messagesDiv.innerHTML = '';
    }, 5000);
}