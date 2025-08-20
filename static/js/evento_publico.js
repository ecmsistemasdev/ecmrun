document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado!');
    
    // Verificar se os botões existem
    const inscricaoBtns = document.querySelectorAll('.inscricao-btn');
    console.log('Botões encontrados:', inscricaoBtns.length);
    
    if (inscricaoBtns.length === 0) {
        console.error('ERRO: Nenhum botão .inscricao-btn encontrado!');
        // Vamos listar todos os botões para ver o que existe
        const todosBotoes = document.querySelectorAll('button');
        console.log('Todos os botões na página:', todosBotoes);
        todosBotoes.forEach((btn, index) => {
            console.log(`Botão ${index}:`, btn.className, btn.textContent);
        });
        return;
    }

    // Event listeners para botões de inscrição
    inscricaoBtns.forEach((btn, index) => {
        console.log(`Configurando event listener para botão ${index}:`, btn);
        
        btn.addEventListener('click', function(e) {
            console.log('BOTÃO CLICADO!', this);
            
            // Prevenir comportamento padrão se for dentro de um form
            e.preventDefault();
            
            const iditem = this.getAttribute('data-iditem');
            const idlote = this.getAttribute('data-idlote');
            
            console.log('*** IDITEM: ', iditem);
            console.log('*** IDLOTE: ', idlote);

            // Validar se iditem e idlote existem
            if (!iditem || iditem === 'null') {
                alert('Erro: ID do item não encontrado');
                console.error('ID do item não encontrado');
                return;
            }
            
            if (!idlote || idlote === 'null') {
                alert('Erro: ID do lote não encontrado');
                console.error('ID do lote não encontrado');
                return;
            }

            console.log('Fazendo requisição para:', `/api/lote-inscricao-item/${iditem}/${idlote}`);

            // ALTERAÇÃO: incluir idlote na URL da API
            fetch(`/api/lote-inscricao-item/${iditem}/${idlote}`)
                .then(response => {
                    console.log('Resposta recebida:', response);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Dados recebidos da API:', data);
                    
                    if (data.error) {
                        alert('Erro ao carregar dados do lote: ' + data.error);
                        return;
                    }

                    // Verificar se o navegador suporta localStorage
                    if (typeof(Storage) !== "undefined") {
                        try {
                            localStorage.setItem('idevento', data.idevento);
                            localStorage.setItem('lote_iditem', data.iditem);
                            localStorage.setItem('lote_idlote', data.idlote);
                            localStorage.setItem('titulo_evento', data.titulo);
                            localStorage.setItem('lote_descricao', data.descricao);
                            localStorage.setItem('lote_vlinscricao', data.vlinscricao);
                            localStorage.setItem('lote_vltaxa', data.vltaxa);
                            localStorage.setItem('lote_vltotal', data.vltotal);
                            localStorage.setItem('lote_vlinscricao_meia', data.vlinscricao_meia);
                            localStorage.setItem('lote_vltaxa_meia', data.vltaxa_meia);
                            localStorage.setItem('lote_vltotal_meia', data.vltotal_meia);
                            
                            console.log('Dados salvos no localStorage');
                        } catch (e) {
                            console.log('localStorage não disponível, usando dados em memória');
                        }

                        // REDIRECIONAR PARA PÁGINA DE INSCRIÇÃO
                        console.log('Redirecionando para página de inscrição...');
                        window.location.href = '/evento-inscricao/' + data.idevento;
                    } else {
                        alert('Seu navegador não suporta armazenamento local');
                    }
                })
                .catch(error => {
                    console.error('Erro na requisição:', error);
                    alert('Erro ao processar solicitação: ' + error.message);
                });
        });
    });
});