// Utilitários para relatórios 200K
// Adicione este arquivo em static/js/relatorios_utils.js

// Função universal para exportar relatórios em PDF
function exportToPDF(tipo) {
    try {
        // Ocultar controles antes de imprimir
        const controles = document.querySelector('.controls');
        const originalDisplay = controles ? controles.style.display : '';
        
        if (controles) {
            controles.style.display = 'none';
        }
        
        // Configurar para impressão
        window.print();
        
        // Restaurar controles após impressão
        setTimeout(() => {
            if (controles) {
                controles.style.display = originalDisplay;
            }
        }, 1000);
        
    } catch (error) {
        console.error('Erro ao exportar PDF:', error);
        alert('Erro ao exportar PDF. Tente novamente.');
    }
}

// Função para aplicar filtros de sexo
function aplicarFiltroSexo(dados, sexoSelecionado) {
    if (!sexoSelecionado || sexoSelecionado === 'AMBOS') {
        return dados;
    }
    
    if (Array.isArray(dados)) {
        return dados.filter(item => item.sexo === sexoSelecionado);
    }
    
    // Para objetos com arrays aninhados (como ranking por modalidade)
    if (typeof dados === 'object' && dados !== null) {
        const resultado = {};
        for (const [key, value] of Object.entries(dados)) {
            if (Array.isArray(value)) {
                resultado[key] = value.filter(item => item.sexo === sexoSelecionado);
            } else {
                resultado[key] = value;
            }
        }
        return resultado;
    }
    
    return dados;
}

// Função para criar filtro de sexo
function criarFiltroSexo(containerId, onChangeCallback) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const filtroHtml = `
        <div class="filtro-sexo">
            <label for="filtro-sexo">Filtrar por sexo:</label>
            <select id="filtro-sexo" onchange="${onChangeCallback}">
                <option value="AMBOS">Ambos</option>
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
            </select>
        </div>
    `;
    
    container.innerHTML = filtroHtml + container.innerHTML;
}

// Função para formatar tempo
function formatarTempo(tempo) {
    if (!tempo) return 'N/A';
    return tempo;
}

// Função para formatar data
function formatarData(data) {
    if (!data) return 'N/A';
    
    try {
        const dataObj = new Date(data);
        return dataObj.toLocaleString('pt-BR');
    } catch (error) {
        return data;
    }
}

// Função para criar tabela responsiva
function criarTabela(dados, colunas, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (!dados || dados.length === 0) {
        container.innerHTML = '<div class="no-data">Nenhum dado encontrado</div>';
        return;
    }
    
    let html = '<div class="table-container"><table><thead><tr>';
    
    // Criar cabeçalho
    colunas.forEach(coluna => {
        html += `<th>${coluna.label}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // Criar linhas
    dados.forEach(item => {
        html += '<tr>';
        colunas.forEach(coluna => {
            let valor = item[coluna.key];
            
            // Aplicar formatação se especificada
            if (coluna.format) {
                valor = coluna.format(valor);
            }
            
            html += `<td>${valor || 'N/A'}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Função para exibir loading
function mostrarLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loading">Carregando dados...</div>';
    }
}

// Função para exibir erro
function mostrarErro(containerId, mensagem) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="error">Erro: ${mensagem}</div>`;
    }
}

// Função para fazer requisição AJAX
async function buscarDados(url) {
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Erro ao carregar dados');
        }
        
        return data;
    } catch (error) {
        console.error('Erro na requisição:', error);
        throw error;
    }
}

// Função para ordenar dados
function ordenarDados(dados, campo, ordem = 'asc') {
    return dados.sort((a, b) => {
        let valorA = a[campo];
        let valorB = b[campo];
        
        // Tratamento para valores numéricos
        if (typeof valorA === 'string' && !isNaN(valorA)) {
            valorA = parseFloat(valorA);
        }
        if (typeof valorB === 'string' && !isNaN(valorB)) {
            valorB = parseFloat(valorB);
        }
        
        if (ordem === 'asc') {
            return valorA > valorB ? 1 : -1;
        } else {
            return valorA < valorB ? 1 : -1;
        }
    });
}

// Função para pesquisar em dados
function pesquisarDados(dados, termo, campos) {
    if (!termo) return dados;
    
    termo = termo.toLowerCase();
    
    return dados.filter(item => {
        return campos.some(campo => {
            const valor = item[campo];
            return valor && valor.toString().toLowerCase().includes(termo);
        });
    });
}

// Função para calcular estatísticas
function calcularEstatisticas(dados) {
    if (!dados || dados.length === 0) {
        return {
            total: 0,
            masculino: 0,
            feminino: 0,
            percentualMasculino: 0,
            percentualFeminino: 0
        };
    }
    
    const total = dados.length;
    const masculino = dados.filter(item => item.sexo === 'M').length;
    const feminino = dados.filter(item => item.sexo === 'F').length;
    
    return {
        total,
        masculino,
        feminino,
        percentualMasculino: ((masculino / total) * 100).toFixed(1),
        percentualFeminino: ((feminino / total) * 100).toFixed(1)
    };
}

// Função para navegação entre relatórios
function voltarParaRelatorios() {
    window.location.href = '/relatorios200k';
}

// Adicionar CSS para elementos criados dinamicamente
const style = document.createElement('style');
style.textContent = `
    .filtro-sexo {
        margin-bottom: 20px;
        text-align: center;
    }
    
    .filtro-sexo label {
        margin-right: 10px;
        font-weight: bold;
    }
    
    .filtro-sexo select {
        padding: 5px 10px;
        border: 1px solid #ddd;
        border-radius: 3px;
        font-size: 14px;
    }
    
    .loading {
        text-align: center;
        padding: 20px;
        color: #666;
    }
    
    .error {
        text-align: center;
        padding: 20px;
        color: #e74c3c;
        background-color: #fadbd8;
        border: 1px solid #e74c3c;
        border-radius: 5px;
        margin: 20px 0;
    }
    
    .no-data {
        text-align: center;
        padding: 20px;
        color: #666;
        font-style: italic;
    }
    
    .table-container {
        overflow-x: auto;
    }
    
    .estatisticas {
        display: flex;
        justify-content: space-around;
        margin: 20px 0;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 5px;
    }
    
    .estatistica-item {
        text-align: center;
    }
    
    .estatistica-valor {
        font-size: 24px;
        font-weight: bold;
        color: #2c3e50;
    }
    
    .estatistica-label {
        font-size: 12px;
        color: #666;
    }
`;

document.head.appendChild(style);
