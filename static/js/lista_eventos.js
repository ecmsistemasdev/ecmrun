document.addEventListener('DOMContentLoaded', function() {
    // Elementos
    const cpfInput = document.getElementById('cpf');
    const dataNascimentoInput = document.getElementById('dataNascimento');
    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('errorMessage');
    const loginContainer = document.getElementById('loginContainer');
    const inscricoesContainer = document.getElementById('inscricoesContainer');
    const inscricoesGrid = document.getElementById('inscricoesGrid');

    // Máscara do CPF
    cpfInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove tudo que não é número
        
        if (value.length <= 11) {
            // Aplica a máscara: 000.000.000-00
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
            e.target.value = value;
        }
    });

    // Máscara da Data de Nascimento
    dataNascimentoInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove tudo que não é número
        
        if (value.length <= 8) {
            // Aplica a máscara: 00/00/0000
            value = value.replace(/(\d{2})(\d)/, '$1/$2');
            value = value.replace(/(\d{2})\/(\d{2})(\d)/, '$1/$2/$3');
            e.target.value = value;
        }
    });

    // Permitir apenas números nos campos
    [cpfInput, dataNascimentoInput].forEach(input => {
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            if (!/[0-9]/.test(char) && e.which !== 8 && e.which !== 0) {
                e.preventDefault();
            }
        });
    });

    // Submit do formulário
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const cpf = cpfInput.value.replace(/[^0-9]/g, '');
        const dataNascimento = dataNascimentoInput.value;
        
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

    function verificarDadosCarregados() {
        const urlParams = new URLSearchParams(window.location.search);
        const cpfParam = urlParams.get('cpf');
        const dataParam = urlParams.get('data');
        
        if (cpfParam && dataParam) {
            // Preencher os campos
            cpfInput.value = formatCPF(cpfParam);
            dataNascimentoInput.value = dataParam;
            
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
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        setTimeout(() => {
            errorMessage.style.display = 'none';
        }, 5000);
    }

    function consultarInscricoes(cpf, dataNascimento) {
        // Mostrar loading
        showLoading();
        
        // Criar FormData
        const formData = new FormData();
        formData.append('cpf', cpf);
        formData.append('data_nascimento', dataNascimento);

        fetch('/api/minhas-inscricoes', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                exibirInscricoes(data.data);
            } else {
                showError(data.message || 'Erro ao consultar inscrições');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Erro na consulta:', error);
            showError('Erro de conexão. Tente novamente.');
        });
    }

    function showLoading() {
        const loadingHtml = `
            <div class="loading-overlay" id="loadingOverlay">
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>Consultando inscrições...</p>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHtml);
    }

    function hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }

    function exibirInscricoes(inscricoes) {
        inscricoesGrid.innerHTML = '';
        
        if (!inscricoes || inscricoes.length === 0) {
            inscricoesGrid.innerHTML = `
                <div class="no-inscricoes">
                    <p>📋 Nenhuma inscrição encontrada</p>
                    <p>Verifique os dados informados e tente novamente.</p>
                </div>
            `;
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
                inscricoesGrid.insertAdjacentHTML('beforeend', card);
            });
        }
        
        loginContainer.style.display = 'none';
        inscricoesContainer.style.display = 'block';
    }

    // Expor funções globalmente para serem acessadas pelos botões
    window.showError = showError;
    window.consultarInscricoes = consultarInscricoes;
    window.exibirInscricoes = exibirInscricoes;
    window.showLoading = showLoading;
    window.hideLoading = hideLoading;
});

function gerarComprovante(idPagamento) {
    if (!idPagamento) {
        window.showError('ID do pagamento não encontrado');
        return;
    }
    
    // Abrir o comprovante em uma nova aba/janela
    window.open(`/comprovante/${idPagamento}`, '_blank');
}

function voltarLogin() {
    document.getElementById('inscricoesContainer').style.display = 'none';
    document.getElementById('loginContainer').style.display = 'block';
    document.getElementById('loginForm').reset();
    document.getElementById('errorMessage').style.display = 'none';
    
    // Limpar parâmetros da URL
    const url = new URL(window.location);
    url.searchParams.delete('cpf');
    url.searchParams.delete('data');
    window.history.replaceState({}, document.title, url.pathname);
}

function voltarPagina() {
    window.history.back();
}

// CSS para o loading (adicionar ao CSS principal se não existir)
const style = document.createElement('style');
style.textContent = `
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    .loading-spinner {
        background: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    
    .spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto 10px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);