// Adicionar no início do script da página
window.addEventListener('beforeunload', function() {
    // Limpar qualquer token restante ao sair da página
    sessionStorage.removeItem('inscricao_token');
});

// Desabilitar F5 e Ctrl+R
document.addEventListener('keydown', function(e) {
    if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
        e.preventDefault();
        alert('Atualização da página não permitida. Retorne à página anterior.');
        return false;
    }
});

// Variáveis globais
let timerInterval;
let tempoRestante = 15 * 60; // 15 minutos em segundos
let dadosEvento = {};

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    carregarDadosEvento();
    carregarEstados();
    iniciarTimer();
    configurarMascaras();
    configurarEventos();
    // Nova função para inicializar os widgets de valores
    inicializarWidgetsValores();
});

// Carregar dados do evento do localStorage
function carregarDadosEvento() {
    dadosEvento = {
        idevento: localStorage.getItem('idevento'),
        iditem: localStorage.getItem('lote_iditem'),
        descricao: localStorage.getItem('lote_descricao'),
        titulo: localStorage.getItem('titulo_evento'),
        vlinscricao: parseFloat(localStorage.getItem('lote_vlinscricao')) || 0,
        vltaxa: parseFloat(localStorage.getItem('lote_vltaxa')) || 0,
        vltotal: parseFloat(localStorage.getItem('lote_vltotal')) || 0,
        vlinscricao_meia: parseFloat(localStorage.getItem('lote_vlinscricao_meia')) || 0,
        vltaxa_meia: parseFloat(localStorage.getItem('lote_vltaxa_meia')) || 0,
        vltotal_meia: parseFloat(localStorage.getItem('lote_vltotal_meia')) || 0
    };

    // Atualizar interface
    document.getElementById('eventoTitulo').textContent = dadosEvento.titulo || 'Evento não identificado';
    document.getElementById('loteInfo').textContent = dadosEvento.descricao || 'Lote não identificado';
}

// Nova função para inicializar os widgets de valores
function inicializarWidgetsValores() {
    // Atualizar widgets com valores padrão (inteira)
    atualizarWidgetsValores(dadosEvento.vlinscricao, dadosEvento.vltaxa, dadosEvento.vltotal);
    
    // Mostrar os widgets
    const widgetDesktop = document.getElementById('valoresWidgetDesktop');
    const widgetMobile = document.getElementById('valoresWidgetMobile');
    
    // Definir informações do lote
    const loteInfo = dadosEvento.descricao || 'Lote Padrão';
    document.getElementById('widgetLoteDesktop').textContent = loteInfo;
    document.getElementById('widgetLoteMobile').textContent = loteInfo;
    
    // Mostrar widgets baseado no tamanho da tela
    if (window.innerWidth >= 768) {
        widgetDesktop.style.display = 'block';
        widgetMobile.style.display = 'none';
    } else {
        widgetDesktop.style.display = 'none';
        widgetMobile.style.display = 'block';
    }
}

// Nova função para atualizar os widgets de valores
function atualizarWidgetsValores(valorInscricao, valorTaxa, valorTotal) {
    // Formatar valores
    const inscricaoFormatado = `R$ ${valorInscricao.toFixed(2).replace('.', ',')}`;
    const taxaFormatado = `R$ ${valorTaxa.toFixed(2).replace('.', ',')}`;
    const totalFormatado = `R$ ${valorTotal.toFixed(2).replace('.', ',')}`;
    
    // Atualizar widget desktop
    document.getElementById('widgetValorInscricaoDesktop').textContent = inscricaoFormatado;
    document.getElementById('widgetValorTaxaDesktop').textContent = taxaFormatado;
    document.getElementById('widgetValorTotalDesktop').textContent = totalFormatado;
    
    // Atualizar widget mobile
    document.getElementById('widgetValorInscricaoMobile').textContent = inscricaoFormatado;
    document.getElementById('widgetValorTaxaMobile').textContent = taxaFormatado;
    document.getElementById('widgetValorTotalMobile').textContent = totalFormatado;
}

// Timer countdown
function iniciarTimer() {
    function atualizarTimer() {
        const minutos = Math.floor(tempoRestante / 60);
        const segundos = tempoRestante % 60;
        document.getElementById('timer').textContent = 
            `${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
        
        if (tempoRestante <= 0) {
            clearInterval(timerInterval);
            mostrarModal('expiredModal');
        } else {
            tempoRestante--;
        }
    }
    
    atualizarTimer();
    timerInterval = setInterval(atualizarTimer, 1000);
}

// Configurar máscaras
function configurarMascaras() {
    configurarMascarasAvancadas();
}

// Nova função para configurar máscaras de forma mais robusta
function configurarMascarasAvancadas() {
    // CPF
    const cpfField = document.getElementById('cpf');
    cpfField.addEventListener('input', function(e) {
        aplicarMascaraCPF(this);
    });
    cpfField.addEventListener('keydown', function(e) {
        // Permite teclas de controle
        if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
            return;
        }
        // Bloqueia caracteres não numéricos
        if (!/[0-9]/.test(e.key)) {
            e.preventDefault();
        }
    });

    // Data de Nascimento
    const dataField = document.getElementById('dataNascimento');
    dataField.addEventListener('input', function(e) {
        aplicarMascaraData(this);
    });
    dataField.addEventListener('keydown', function(e) {
        if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
            return;
        }
        if (!/[0-9]/.test(e.key)) {
            e.preventDefault();
        }
    });

    // Celular
    const celularField = document.getElementById('celular');
    celularField.addEventListener('input', function(e) {
        aplicarMascaraTelefone(this);
    });
    celularField.addEventListener('keydown', function(e) {
        if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
            return;
        }
        if (!/[0-9]/.test(e.key)) {
            e.preventDefault();
        }
    });

    // Telefone de Emergência
    const telEmergenciaField = document.getElementById('telEmergencia');
    telEmergenciaField.addEventListener('input', function(e) {
        aplicarMascaraTelefone(this);
    });
    telEmergenciaField.addEventListener('keydown', function(e) {
        if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
            return;
        }
        if (!/[0-9]/.test(e.key)) {
            e.preventDefault();
        }
    });
}

// Função para aplicar máscara de CPF
function aplicarMascaraCPF(campo) {
    let valor = campo.value.replace(/\D/g, '');
    const posicaoCursor = campo.selectionStart;
    const valorAnterior = campo.value;
    
    if (valor.length <= 11) {
        valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
        valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
        valor = valor.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    }
    
    campo.value = valor;
    
    // Ajustar posição do cursor
    setTimeout(() => {
        let novaPosicao = posicaoCursor;
        if (valor.length > valorAnterior.length) {
            // Se adicionou caracteres especiais, ajustar cursor
            if (valor.charAt(posicaoCursor - 1) === '.' || valor.charAt(posicaoCursor - 1) === '-') {
                novaPosicao = posicaoCursor + 1;
            }
        }
        campo.setSelectionRange(novaPosicao, novaPosicao);
    }, 0);
}

// Função para aplicar máscara de data
function aplicarMascaraData(campo) {
    let valor = campo.value.replace(/\D/g, '');
    const posicaoCursor = campo.selectionStart;
    const valorAnterior = campo.value;
    
    if (valor.length <= 8) {
        valor = valor.replace(/(\d{2})(\d)/, '$1/$2');
        valor = valor.replace(/(\d{2})\/(\d{2})(\d)/, '$1/$2/$3');
    }
    
    campo.value = valor;
    
    // Ajustar posição do cursor
    setTimeout(() => {
        let novaPosicao = posicaoCursor;
        if (valor.length > valorAnterior.length) {
            if (valor.charAt(posicaoCursor - 1) === '/') {
                novaPosicao = posicaoCursor + 1;
            }
        }
        campo.setSelectionRange(novaPosicao, novaPosicao);
    }, 0);
}

// Função para aplicar máscara de telefone
function aplicarMascaraTelefone(campo) {
    let valor = campo.value.replace(/\D/g, '');
    const posicaoCursor = campo.selectionStart;
    const valorAnterior = campo.value;
    
    if (valor.length <= 11) {
        valor = valor.replace(/(\d{2})(\d)/, '($1) $2');
        valor = valor.replace(/(\d{4,5})(\d{4})$/, '$1-$2');
    }
    
    campo.value = valor;
    
    // Ajustar posição do cursor
    setTimeout(() => {
        let novaPosicao = posicaoCursor;
        if (valor.length > valorAnterior.length) {
            const caracterAtual = valor.charAt(posicaoCursor - 1);
            if (['(', ')', ' ', '-'].includes(caracterAtual)) {
                novaPosicao = posicaoCursor + 1;
            }
        }
        campo.setSelectionRange(novaPosicao, novaPosicao);
    }, 0);
}

// Configurar eventos
function configurarEventos() {
    // Permitir apenas números nos campos específicos
    ['cpf', 'dataNascimento', 'celular', 'telEmergencia'].forEach(id => {
        document.getElementById(id).addEventListener('input', function(e) {
            // Remove tudo que não for número
            let value = e.target.value.replace(/\D/g, '');
            
            // Aplica a máscara dependendo do campo
            if (id === 'cpf') {
                value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            } else if (id === 'dataNascimento') {
                value = value.replace(/(\d{2})(\d{2})(\d{4})/, '$1/$2/$3');
            } else if (id === 'celular' || id === 'telEmergencia') {
                value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            }
            
            e.target.value = value;
        });
        
        // Previne entrada de caracteres não numéricos
        document.getElementById(id).addEventListener('keypress', function(e) {
            if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'Tab', 'Enter', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
            }
        });
    });

    // Campos em maiúsculo
    ['nome', 'sobrenome', 'contEmergencia', 'nomepeito', 'cupom'].forEach(id => {
        document.getElementById(id).addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    });

    // Validação do CPF ao sair do campo - COM MODAL DE LOADING
    $('#cpf').on('blur', function() {
        const cpf = $(this).val().replace(/\D/g, '');
        
        if (cpf.length !== 11) {
            return;
        }

        // Mostrar modal de loading
        mostrarModal('loadingCpfModal');

        // Primeira chamada para validar o formato do CPF
        fetch(`/validar-cpf?cpf=${cpf}`)
            .then(response => response.json())
            .then(data => {
                if (!data.valid) {
                    fecharModal('loadingCpfModal');
                    showModal('CPF inválido');
                    $(this).val('');
                    setTimeout(() => {
                        $(this).focus();
                    }, 100);
                    return Promise.reject('CPF inválido');
                }
                
                const idevento = dadosEvento.idevento;
                return fetch(`/verifica-cpf-inscrito/${idevento}?cpf=${cpf}`);
            })
            .then(response => response.json())
            .then(data => {
                if (data.exists) {
                    fecharModal('loadingCpfModal');
                    showModal('CPF já inscrito para o evento.');
                    $(this).val('');
                    setTimeout(() => {
                        $(this).focus();
                    }, 100);
                    return Promise.reject('CPF já inscrito');
                }
                
                // Nova verificação: buscar dados existentes do CPF
                return fetch(`/buscar-dados-cpf?cpf=${cpf}`);
            })
            .then(response => response.json())
            .then(data => {
                fecharModal('loadingCpfModal');
                if (data.success) {
                    // Preencher formulário com dados encontrados - SEM MODAL
                    preencherFormularioComDados(data.dados);
                } else {
                    fecharModal('loadingPagamentoModal'); 
                    alert('Erro ao salvar inscrição: ' + (data.mensagem || 'Erro desconhecido'));
                }

                // Se não encontrou dados, não faz nada (formulário continua em branco)
            })
            .catch(error => {
                fecharModal('loadingCpfModal');
                if (error !== 'CPF inválido' && error !== 'CPF já inscrito') {
                    console.error('Erro na validação do CPF:', error);
                }
            });
    });

    // Validação de data
    document.getElementById('dataNascimento').addEventListener('blur', function() {
        if (this.value) {
            if (validarData(this.value)) {
                calcularIdadeEValores();
            } else {
                mostrarModal('dataInvalidaModal');
                this.focus();
            }
        }
    });

    // Estado - MODIFICADO para não usar cidade padrão quando mudado manualmente
    document.getElementById('estado').addEventListener('change', function() {
        carregarCidades(this.value); // Remove o segundo parâmetro
    });           

    // Estado
    document.getElementById('estado').addEventListener('change', function() {
        carregarCidades(this.value);
    });

    // Termo de aceite
    document.getElementById('termoAceite').addEventListener('change', function() {
        document.getElementById('btnProximo').disabled = !this.checked;
    });

    // Submit do formulário - COM MODAL DE LOADING
    document.getElementById('inscricaoForm').addEventListener('submit', function(e) {
        e.preventDefault();
        if (validarFormulario()) {
            // Mostrar modal de loading do pagamento
            mostrarModal('loadingPagamentoModal');
            salvarInscricao();
        }
    });

    // Event listener para redimensionamento da janela
    window.addEventListener('resize', function() {
        const widgetDesktop = document.getElementById('valoresWidgetDesktop');
        const widgetMobile = document.getElementById('valoresWidgetMobile');
        
        if (window.innerWidth >= 768) {
            widgetDesktop.style.display = 'block';
            widgetMobile.style.display = 'none';
        } else {
            widgetDesktop.style.display = 'none';
            widgetMobile.style.display = 'block';
        }
    });
}

// Função para mostrar modal de alerta
function showModal(mensagem) {
    document.getElementById('alertModalText').textContent = mensagem;
    document.getElementById('alertModal').style.display = 'block';
}

// Nova função para preencher formulário com dados existentes
function preencherFormularioComDados(dados) {
    // Preencher campos básicos
    document.getElementById('nome').value = dados.nome || '';
    document.getElementById('sobrenome').value = dados.sobrenome || '';
    document.getElementById('email').value = dados.email || '';
    
    // Preencher celular com máscara aplicada
    if (dados.celular) {
        // Remove qualquer formatação existente e aplica a máscara
        const celularLimpo = dados.celular.replace(/\D/g, '');
        const celularFormatado = celularLimpo.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        document.getElementById('celular').value = celularFormatado;
    }
    
    // Preencher data de nascimento e disparar evento para calcular valores
    if (dados.dtnascimento) {
        document.getElementById('dataNascimento').value = dados.dtnascimento;
        // Simular evento blur para calcular idade e valores
        const event = new Event('blur', { bubbles: true });
        document.getElementById('dataNascimento').dispatchEvent(event);
    }
    
    // Preencher sexo
    if (dados.sexo) {
        const radioSexo = document.querySelector(`input[name="sexo"][value="${dados.sexo}"]`);
        if (radioSexo) {
            radioSexo.checked = true;
        }
    }
    
    // Preencher estado e depois cidade
    if (dados.estado) {
        document.getElementById('estado').value = dados.estado;
        
        // Carregar cidades do estado e definir a cidade
        if (dados.id_cidade) {
            carregarCidades(dados.estado, dados.id_cidade);
        } else {
            carregarCidades(dados.estado);
        }
    }
}

// Carregar estados com valor padrão
function carregarEstados() {
    fetch('/listar-estados')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('estado');
                data.estados.forEach(estado => {
                    const option = document.createElement('option');
                    option.value = estado.uf;
                    option.textContent = estado.nome;
                    select.appendChild(option);
                });
                
                // Definir Rondônia como padrão
                select.value = 'RO';
                
                // Carregar cidades de Rondônia e definir Porto Velho como padrão
                carregarCidades('RO', 7535);
            }
        })
        .catch(error => console.error('Erro ao carregar estados:', error));
}

// Carregar cidades com possibilidade de valor padrão
function carregarCidades(uf, cidadePadrao = null) {
    const cidadeSelect = document.getElementById('cidade');
    
    if (!uf) {
        cidadeSelect.innerHTML = '<option value="">Primeiro selecione um estado</option>';
        cidadeSelect.disabled = true;
        return;
    }

    cidadeSelect.innerHTML = '<option value="">Carregando...</option>';
    cidadeSelect.disabled = true;

    fetch(`/listar-cidades?uf=${uf}`)
        .then(response => response.json())
        .then(data => {
            cidadeSelect.innerHTML = '<option value="">Selecione uma cidade</option>';
            
            if (data.success) {
                data.cidades.forEach(cidade => {
                    const option = document.createElement('option');
                    option.value = cidade.id_cidade;
                    option.textContent = cidade.descricao;
                    cidadeSelect.appendChild(option);
                });
                cidadeSelect.disabled = false;
                
                // Definir cidade padrão se fornecida
                if (cidadePadrao) {
                    cidadeSelect.value = cidadePadrao;
                }
            }
        })
        .catch(error => {
            console.error('Erro ao carregar cidades:', error);
            cidadeSelect.innerHTML = '<option value="">Erro ao carregar cidades</option>';
        });
}

// Calcular idade e valores - MODIFICADO para atualizar os widgets
function calcularIdadeEValores() {
    const dataNasc = document.getElementById('dataNascimento').value;
    if (!dataNasc || !validarData(dataNasc)) return;

    const [dia, mes, ano] = dataNasc.split('/');
    const nascimento = new Date(ano, mes - 1, dia);
    
    // Data do evento (pode ser dinâmica)
    const dataEvento = new Date(2026, 0, 18); // 18/01/2026
    
    let idade = dataEvento.getFullYear() - nascimento.getFullYear();
    const diffMes = dataEvento.getMonth() - nascimento.getMonth();
    
    if (diffMes < 0 || (diffMes === 0 && dataEvento.getDate() < nascimento.getDate())) {
        idade--;
    }

    // Definir valores baseado na idade
    let valorInscricao, valorTaxa, valorTotal;
    
    if (idade >= 60) {
        valorInscricao = dadosEvento.vlinscricao_meia;
        valorTaxa = dadosEvento.vltaxa_meia;
        valorTotal = dadosEvento.vltotal_meia;
    } else {
        valorInscricao = dadosEvento.vlinscricao;
        valorTaxa = dadosEvento.vltaxa;
        valorTotal = dadosEvento.vltotal;
    }

    // Atualizar interface original
    document.getElementById('valorInscricao').textContent = `R$ ${valorInscricao.toFixed(2).replace('.', ',')}`;
    document.getElementById('valorTaxa').textContent = `R$ ${valorTaxa.toFixed(2).replace('.', ',')}`;
    document.getElementById('valorTotal').textContent = `R$ ${valorTotal.toFixed(2).replace('.', ',')}`;
    
    // Atualizar os widgets flutuantes
    atualizarWidgetsValores(valorInscricao, valorTaxa, valorTotal);
    
    // Mostrar container de valores original
    document.getElementById('valoresContainer').style.display = 'block';
}

// Validar CPF - CORRIGIDA para não interferir com as validações modais
function validarCPF(cpf) {
    cpf = cpf.replace(/\D/g, '');
    
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
        return false; // Removido mostrarErro daqui
    }

    let soma = 0;
    for (let i = 0; i < 9; i++) {
        soma += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let resto = 11 - (soma % 11);
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.charAt(9))) {
        return false; // Removido mostrarErro daqui
    }

    soma = 0;
    for (let i = 0; i < 10; i++) {
        soma += parseInt(cpf.charAt(i)) * (11 - i);
    }
    resto = 11 - (soma % 11);
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.charAt(10))) {
        return false; // Removido mostrarErro daqui
    }

    return true; // CPF válido
}

// Validar data
function validarData(data) {
    const regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    const match = data.match(regex);
    
    if (!match) return false;
    
    const dia = parseInt(match[1]);
    const mes = parseInt(match[2]);
    const ano = parseInt(match[3]);
    
    const dataObj = new Date(ano, mes - 1, dia);
    
    if (dataObj.getDate() !== dia || dataObj.getMonth() !== (mes - 1) || dataObj.getFullYear() !== ano) {
        return false;
    }
    
    const hoje = new Date();
    if (dataObj >= hoje) {
        return false;
    }
    
    return true;
}

// Validar email
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

let campoParaFocar = null;

// Validar formulário com mensagens modais específicas
function validarFormulario() {
    // Email
    const email = document.getElementById('email').value.trim();
    if (!email) {
        mostrarCampoObrigatorio('E-mail é obrigatório', 'email');
        return false;
    }
    if (!validarEmail(email)) {
        mostrarCampoObrigatorio('Por favor, insira um e-mail válido', 'email');
        return false;
    }

    // CPF
    const cpf = document.getElementById('cpf').value.replace(/\D/g, '');
    if (!cpf) {
        mostrarCampoObrigatorio('CPF é obrigatório', 'cpf');
        return false;
    }
    if (!validarCPF(cpf)) {
        mostrarCampoObrigatorio('Por favor, insira um CPF válido', 'cpf');
        return false;
    }

    // Nome
    const nome = document.getElementById('nome').value.trim();
    if (!nome) {
        mostrarCampoObrigatorio('Nome é obrigatório', 'nome');
        return false;
    }

    // Sobrenome
    const sobrenome = document.getElementById('sobrenome').value.trim();
    if (!sobrenome) {
        mostrarCampoObrigatorio('Sobrenome é obrigatório', 'sobrenome');
        return false;
    }

    // Data de nascimento
    const dataNasc = document.getElementById('dataNascimento').value;
    if (!dataNasc) {
        mostrarCampoObrigatorio('Data de nascimento é obrigatória', 'dataNascimento');
        return false;
    }
    if (!validarData(dataNasc)) {
        mostrarCampoObrigatorio('Por favor, insira uma data de nascimento válida', 'dataNascimento');
        return false;
    }

    // Celular
    const celular = document.getElementById('celular').value.replace(/\D/g, '');
    if (!celular) {
        mostrarCampoObrigatorio('Celular é obrigatório', 'celular');
        return false;
    }
    if (celular.length !== 11) {
        mostrarCampoObrigatorio('Por favor, insira um celular válido com DDD', 'celular');
        return false;
    }

    // Sexo
    const sexo = document.querySelector('input[name="sexo"]:checked');
    if (!sexo) {
        mostrarCampoObrigatorio('Por favor, selecione o sexo', 'masculino');
        return false;
    }

    // Camiseta
    const camiseta = document.querySelector('input[name="camiseta"]:checked');
    if (!camiseta) {
        mostrarCampoObrigatorio('Por favor, selecione o tamanho da camiseta', 'camisetaPP');
        return false;
    }

    // Estado
    const estado = document.getElementById('estado').value;
    if (!estado) {
        mostrarCampoObrigatorio('Por favor, selecione um estado', 'estado');
        return false;
    }

    // Cidade
    const cidade = document.getElementById('cidade').value;
    if (!cidade) {
        mostrarCampoObrigatorio('Por favor, selecione uma cidade', 'cidade');
        return false;
    }

    // Forma de pagamento
    const formaPagamento = document.querySelector('input[name="formaPagamento"]:checked');
    if (!formaPagamento) {
        mostrarCampoObrigatorio('Por favor, selecione a forma de pagamento', 'pix');
        return false;
    }

    // Termo de aceite
    const termoAceite = document.getElementById('termoAceite').checked;
    if (!termoAceite) {
        mostrarCampoObrigatorio('Você deve aceitar os termos de responsabilidade para prosseguir', 'termoAceite');
        return false;
    }

    // Se chegou até aqui, todos os campos estão válidos
    return true;
}

// Função para mostrar modal de campo obrigatório
function mostrarCampoObrigatorio(mensagem, campoId) {
    campoParaFocar = campoId;
    document.getElementById('campoObrigatorioText').textContent = mensagem;
    document.getElementById('campoObrigatorioModal').style.display = 'block';
}

// Função para fechar modal e focar no campo
function fecharModalEFocar() {
    document.getElementById('campoObrigatorioModal').style.display = 'none';
    
    if (campoParaFocar) {
        const campo = document.getElementById(campoParaFocar);
        if (campo) {
            // Scroll para o campo
            campo.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Focar no campo após um pequeno delay para garantir que o modal fechou
            setTimeout(() => {
                campo.focus();
                
                // Se for um campo de texto, selecionar o conteúdo
                if (campo.type === 'text' || campo.type === 'email') {
                    campo.select();
                }
            }, 100);
        }
        campoParaFocar = null;
    }
}

// Salvar inscrição (função consolidada)
function salvarInscricao() {
    // Calcular idade
    const dataNasc = document.getElementById('dataNascimento').value;
    const [dia, mes, ano] = dataNasc.split('/');
    const nascimento = new Date(ano, mes - 1, dia);
    const dataEvento = new Date(2026, 0, 18); // 18/01/2026
    
    let idade = dataEvento.getFullYear() - nascimento.getFullYear();
    const diffMes = dataEvento.getMonth() - nascimento.getMonth();
    
    if (diffMes < 0 || (diffMes === 0 && dataEvento.getDate() < nascimento.getDate())) {
        idade--;
    }

    // Preparar dados para envio
    const dadosInscricao = {
        idevento: dadosEvento.idevento,
        iditemevento: dadosEvento.iditem,
        cpf: document.getElementById('cpf').value.replace(/\D/g, ''),
        email: document.getElementById('email').value.trim(),
        nome: document.getElementById('nome').value.trim(),
        sobrenome: document.getElementById('sobrenome').value.trim(),
        dtnascimento: document.getElementById('dataNascimento').value,
        idade: idade,
        celular: document.getElementById('celular').value.replace(/\D/g, ''),
        sexo: document.querySelector('input[name="sexo"]:checked').value,
        nomepeito: document.getElementById('nomepeito').value.trim().toUpperCase() || null,
        equipe: document.getElementById('equipe').value.trim().toUpperCase() || null,
        camiseta: document.querySelector('input[name="camiseta"]:checked').value,
        tel_emergencia: document.getElementById('telEmergencia').value.replace(/\D/g, '') || null,
        cont_emergencia: document.getElementById('contEmergencia').value.trim().toUpperCase() || null,
        estado: parseInt(document.getElementById('estado').value),
        id_cidade: parseInt(document.getElementById('cidade').value),
        cupom: document.getElementById('cupom').value.trim().toUpperCase() || null,
        formapgto: document.querySelector('input[name="formaPagamento"]:checked').value,
        
        // Valores baseados na idade
        vlinscricao: idade >= 60 ? dadosEvento.vlinscricao_meia : dadosEvento.vlinscricao,
        vltaxa: idade >= 60 ? dadosEvento.vltaxa_meia : dadosEvento.vltaxa,
        vltotal: idade >= 60 ? dadosEvento.vltotal_meia : dadosEvento.vltotal,
        
        status: 'P' // Pendente
    };

    // Enviar dados para o backend
    fetch('/evento_salvar_inscricao', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dadosInscricao)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Salvar ID da inscrição para próximas etapas
            localStorage.setItem('inscricao_id', data.inscricao_id);
            
            // Redirecionar baseado na forma de pagamento
            const formaPagamento = document.querySelector('input[name="formaPagamento"]:checked').value;
            if (formaPagamento === 'PIX') {
                // Calcular valores finais baseados na idade
                const vlinscricaoFinal = idade >= 60 ? dadosEvento.vlinscricao_meia : dadosEvento.vlinscricao;
                const vltaxaFinal = idade >= 60 ? dadosEvento.vltaxa_meia : dadosEvento.vltaxa;
                const vltotalFinal = idade >= 60 ? dadosEvento.vltotal_meia : dadosEvento.vltotal;
                
                // Salvar dados do usuário para a página de pagamento
                localStorage.setItem('id_evento', dadosInscricao.idevento);
                localStorage.setItem('user_name', `${dadosInscricao.nome} ${dadosInscricao.sobrenome}`);
                localStorage.setItem('user_email', dadosInscricao.email);
                localStorage.setItem('user_cpf', dadosInscricao.cpf);
                localStorage.setItem('user_idatleta', data.inscricao_id.toString());
                
                // Salvar valores financeiros
                localStorage.setItem('valoratual', vlinscricaoFinal.toFixed(2));
                localStorage.setItem('valortaxa', vltaxaFinal.toFixed(2));
                localStorage.setItem('valortotal', vltotalFinal.toFixed(2));
                
                // Debug - verificar se os dados foram salvos
                console.log('Dados salvos no localStorage:');
                console.log('user_name:', localStorage.getItem('user_name'));
                console.log('user_email:', localStorage.getItem('user_email'));
                console.log('valoratual:', localStorage.getItem('valoratual'));
                console.log('valortaxa:', localStorage.getItem('valortaxa'));
                console.log('valortotal:', localStorage.getItem('valortotal'));
                
                window.location.href = '/pagamento';
            } else {
                // Calcular valores finais baseados na idade
                const vlinscricaoFinal = idade >= 60 ? dadosEvento.vlinscricao_meia : dadosEvento.vlinscricao;
                const vltaxaFinal = idade >= 60 ? dadosEvento.vltaxa_meia : dadosEvento.vltaxa;
                const vltotalFinal = idade >= 60 ? dadosEvento.vltotal_meia : dadosEvento.vltotal;

                // Salvar dados do usuário para a página de pagamento
                localStorage.setItem('id_evento', dadosInscricao.idevento);
                localStorage.setItem('user_name', `${dadosInscricao.nome} ${dadosInscricao.sobrenome}`);
                localStorage.setItem('user_email', dadosInscricao.email);
                localStorage.setItem('user_cpf', dadosInscricao.cpf);
                localStorage.setItem('user_idatleta', data.inscricao_id.toString());
                
                // Salvar valores financeiros
                localStorage.setItem('valoratual', vlinscricaoFinal.toFixed(2));
                localStorage.setItem('valortaxa', vltaxaFinal.toFixed(2));
                localStorage.setItem('valortotal', vltotalFinal.toFixed(2));
                
                // Debug - verificar se os dados foram salvos
                console.log('Dados salvos no localStorage:');
                console.log('user_name:', localStorage.getItem('user_name'));
                console.log('user_cpf:', localStorage.getItem('user_cpf'));
                console.log('user_email:', localStorage.getItem('user_email'));
                console.log('valoratual:', localStorage.getItem('valoratual'));
                console.log('valortaxa:', localStorage.getItem('valortaxa'));
                console.log('valortotal:', localStorage.getItem('valortotal'));

                // Validar se todos os campos necessários estão presentes
                if (!vltotalFinal || !localStorage.getItem('user_name') || !localStorage.getItem('user_cpf') || !localStorage.getItem('user_email')) {
                    console.error('Dados obrigatórios faltando:', {
                        vltotalFinal,
                        userName: localStorage.getItem('user_name'),
                        userCPF: localStorage.getItem('user_cpf'),
                        userEmail: localStorage.getItem('user_email')
                    });
                    alert('Dados incompletos. Por favor, verifique se todos os campos estão preenchidos.');
                    return;
                }

                // Preparar dados para enviar ao backend
                const requestData = {
                    valortotal: vltotalFinal,
                    valortaxa: vltaxaFinal,
                    user_name: localStorage.getItem('user_name'),
                    user_email: localStorage.getItem('user_email'),
                    user_cpf: localStorage.getItem('user_cpf')
                };
                localStorage.setItem('valoratual', vlinscricaoFinal.toString());
                localStorage.setItem('vlinscricao', vlinscricaoFinal.toString());
                localStorage.setItem('valortotal', vltotalFinal.toString());

                // localStorage.setItem('valoratual', vlinscricao.toString());
                // localStorage.setItem('vlinscricao', vlinscricao.toString());
                // localStorage.setItem('valortotal', valorTotal.toString());

                console.log('Dados sendo enviados:', requestData);
                
                window.location.href = '/checkout';
            }
        } else {
            alert('Erro ao salvar inscrição: ' + (data.mensagem || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        fecharModal('loadingPagamentoModal'); 
        console.error('Erro:', error);
        alert('Erro ao processar inscrição. Tente novamente.');
    });
}

// Funções de utilidade
function mostrarErro(elementId, mensagem) {
    const element = document.getElementById(elementId);
    element.textContent = mensagem;
    element.style.display = 'block';
}

function esconderErro(elementId) {
    const element = document.getElementById(elementId);
    element.style.display = 'none';
}

function mostrarModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function fecharModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function voltarPaginaAnterior() {
    window.history.back();
}

// Cleanup ao sair da página
window.addEventListener('beforeunload', function() {
    if (timerInterval) {
        clearInterval(timerInterval);
    }
});