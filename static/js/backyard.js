document.addEventListener('DOMContentLoaded', function() {
    const inscricaoBtns = document.querySelectorAll('.inscricao-btn');

    // Event listeners para botões de inscrição
    inscricaoBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const iditem = this.getAttribute('data-iditem');

            // Buscar dados do lote selecionado
            fetch(`/api/lote-inscricao/${iditem}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Erro ao carregar dados do lote: ' + data.error);
                        return;
                    }
                    console.log('*** IDEVENTO: ', data.idevento);

                    // Armazenar dados do lote no localStorage
                    localStorage.setItem('idevento', data.idevento);
                    localStorage.setItem('lote_iditem', data.iditem);
                    localStorage.setItem('titulo_evento', data.titulo);
                    localStorage.setItem('lote_descricao', data.descricao);
                    localStorage.setItem('lote_vlinscricao', data.vlinscricao);
                    localStorage.setItem('lote_vltaxa', data.vltaxa);
                    localStorage.setItem('lote_vltotal', data.vltotal);
                    localStorage.setItem('lote_vlinscricao_meia', data.vlinscricao_meia);
                    localStorage.setItem('lote_vltaxa_meia', data.vltaxa_meia);
                    localStorage.setItem('lote_vltotal_meia', data.vltotal_meia);

                    // ALTERAÇÃO: Redirecionar para nova página de inscrição
                    window.location.href = '/gerar-token-inscricao/' + data.idevento;
                    //window.location.href = '/inscricao-evento/' + data.idevento;

                })
                .catch(error => {
                    console.error('Erro:', error);
                    alert('Erro ao processar solicitação');
                });
        });
    });
});