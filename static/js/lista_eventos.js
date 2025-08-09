$(document).ready(function() {
    // Aplicar máscaras
    $('#cpf').mask('000.000.000-00');
    $('#dataNascimento').mask('00/00/0000');

    // Permitir apenas números
    $('#cpf, #dataNascimento').on('input', function() {
        this.value = this.value.replace(/[^0-9./\-]/g, '');
    });

    // Submit do formulário
    $('#loginForm').on('submit', function(e) {
        e.preventDefault();
        
        const cpf = $('#cpf').val().replace(/[^0-9]/g, '');
        const dataNascimento = $('#dataNascimento').val();
        
        // Validações
        if (cpf.length !== 11) {
            showError('CPF deve conter 11 dígitos');
            return;
        }
        
        if (!isValidDate(dataNascimento)) {
            showError('Data de nascimento inválida');
            return;
        }
        
        // Fazer consulta
        consultarInscricoes(cpf, dataNascimento);
    });

    // Verificar se há dados salvos para carregar automaticamente
    verificarDadosCarregados();
});

function verificarDadosCarregados() {
    // Verificar se há parâmetros na URL ou dados salvos
    const urlParams = new URLSearchParams(window.location.search);
    const cpfParam = urlParams.get('cpf');
    const dataParam = urlParams.get('data');
    
    if (cpfParam && dataParam) {
        // Preencher os campos
        $('#cpf').val(formatCPF(cpfParam));
        $('#dataNascimento').val(dataParam);
        
        // Fazer a consulta automaticamente
        consultarInscricoes(cpfParam, dataParam);
    }
}

function formatCPF(cpf) {
    // Remove tudo que não é dígito
    cpf = cpf.replace(/\D/g, '');
    
    // Aplica a máscara
    if (cpf.length === 11) {
        return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }
    return cpf;
}

function isValidDate(dateString) {
    const regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    const match = dateString.match(regex);
    
    if (!match) return false;
    
    const day = parseInt(match[1], 10);
    const month = parseInt(match[2], 10);
    const year = parseInt(match[3], 10);
    
    const date = new Date(year, month - 1, day);
    
    return date.getFullYear() === year &&
        date.getMonth() === month - 1 &&
        date.getDate() === day &&
        month >= 1 && month <= 12 &&
        day >= 1 && day <= 31;
}

function showError(message) {
    $('#errorMessage').text(message).show();
    setTimeout(() => {
        $('#errorMessage').hide();
    }, 5000);
}

function consultarInscricoes(cpf, dataNascimento) {
    // Mostrar loading
    showLoading();
    
    $.ajax({
        url: '/api/minhas-inscricoes',
        method: 'POST',
        data: {
            cpf: cpf,
            data_nascimento: dataNascimento
        },
        success: function(response) {
            hideLoading();
            if (response.success) {
                exibirInscricoes(response.data);
            } else {
                showError(response.message || 'Erro ao consultar inscrições');
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            console.error('Erro na consulta:', error);
            showError('Erro de conexão. Tente novamente.');
        }
    });
}

function showLoading() {
    // Adicionar indicador de carregamento
    const loadingHtml = `
        <div class="loading-overlay" id="loadingOverlay">
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>Consultando inscrições...</p>
            </div>
        </div>
    `;
    $('body').append(loadingHtml);
}

function hideLoading() {
    $('#loadingOverlay').remove();
}

function exibirInscricoes(inscricoes) {
    const grid = $('#inscricoesGrid');
    grid.empty();
    
    if (!inscricoes || inscricoes.length === 0) {
        grid.append(`
            <div class="no-inscricoes">
                <p>📋 Nenhuma inscrição encontrada</p>
                <p>Verifique os dados informados e tente novamente.</p>
            </div>
        `);
    } else {
        inscricoes.forEach(inscricao => {
            const card = `
                <div class="inscricao-card">
                    <div class="card-header">
                        <div class="evento-nome">${inscricao.DESCRICAO || 'Evento'}</div>
                        <div class="evento-data">📅 ${inscricao.DTEVENTO || 'Data não informada'}</div>
                    </div>
                    
                    <div class="card-content">
                        <div class="info-row">
                            <span class="info-label">Modalidade:</span>
                            <span class="info-value">
                                <span class="modalidade-badge">${inscricao.KM_DESCRICAO || 'Não informado'}</span>
                            </span>
                        </div>
                        
                        <div class="info-row">
                            <span class="info-label">Valor:</span>
                            <span class="info-value valor-destaque">R$ ${inscricao.VLTOTAL || '0,00'}</span>
                        </div>
                        
                        <div class="info-row">
                            <span class="info-label">Data da Inscrição:</span>
                            <span class="info-value">${inscricao.DTPAGAMENTO || 'Não informado'}</span>
                        </div>
                        
                        ${inscricao.STATUS ? `
                        <div class="info-row">
                            <span class="info-label">Status:</span>
                            <span class="info-value status-${inscricao.STATUS.toLowerCase()}">${inscricao.STATUS}</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    <button class="btn-comprovante" onclick="gerarComprovante('${inscricao.IDPAGAMENTO || ''}')">
                        📄 Gerar Comprovante
                    </button>
                </div>
            `;
            grid.append(card);
        });
    }
    
    $('#loginContainer').hide();
    $('#inscricoesContainer').show();
}

function gerarComprovante(idPagamento) {
    if (!idPagamento) {
        showError('ID do pagamento não encontrado');
        return;
    }
    
    // Abrir o comprovante em uma nova aba/janela
    window.open(`/comprovante/${idPagamento}`, '_blank');
}

function voltarLogin() {
    $('#inscricoesContainer').hide();
    $('#loginContainer').show();
    $('#loginForm')[0].reset();
    $('#errorMessage').hide();
    
    // Limpar parâmetros da URL
    const url = new URL(window.location);
    url.searchParams.delete('cpf');
    url.searchParams.delete('data');
    window.history.replaceState({}, document.title, url.pathname);
}

function voltarPagina() {
    window.history.back();
}