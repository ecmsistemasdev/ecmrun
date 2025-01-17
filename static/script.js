document.addEventListener('DOMContentLoaded', function () {
    const cpfInput = document.getElementById('cpf');
    const phoneInput = document.getElementById('celular');
    const cepInput = document.getElementById('cep');
    const infoDisplay = document.getElementById('info');
    const regulamentoDisplay = document.getElementById('regulamento');
    
    // Máscara para CPF
    cpfInput.addEventListener('input', function (event) {
        let inputValue = event.target.value.replace(/\D/g, '');
        inputValue = inputValue.substring(0, 11);

        if (inputValue.length > 10) {
            inputValue = inputValue.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        } else if (inputValue.length > 7) {
            inputValue = inputValue.replace(/(\d{3})(\d{3})(\d{2})/, '$1.$2-$3');
        } else if (inputValue.length > 3) {
            inputValue = inputValue.replace(/(\d{3})(\d{0,3})/, '$1.$2');
        } else if (inputValue.length > 0) {
            inputValue = inputValue.replace(/(\d{1,3})/, '$1');
        }

        event.target.value = inputValue;
    });

    // Máscara para Telefone
    phoneInput.addEventListener('input', function (event) {
        let inputValue = event.target.value.replace(/\D/g, '');
        inputValue = inputValue.substring(0, 11);

        if (inputValue.length > 10) {
            inputValue = inputValue.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        } else if (inputValue.length > 6) {
            inputValue = inputValue.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
        } else if (inputValue.length > 2) {
            inputValue = inputValue.replace(/(\d{2})(\d+)/, '($1) $2');
        }

        event.target.value = inputValue;
    });

    // Máscara para CEP
    cepInput.addEventListener('input', function (event) {
        let inputValue = event.target.value.replace(/\D/g, '');
        inputValue = inputValue.substring(0, 8);

        if (inputValue.length > 5) {
            inputValue = inputValue.replace(/(\d{5})(\d{3})/, '$1-$2');
        } else if (inputValue.length > 0) {
            inputValue = inputValue.replace(/(\d{5})/, '$1');
        }

        event.target.value = inputValue;
    });

    // Função para carregar o conteúdo de info.txt
    function loadInfo() {
        fetch('/static/info.txt')
            .then(response => {
                console.log('Status da resposta:', response.status); // Log do status da resposta

                if (!response.ok) {
                    throw new Error('Erro ao carregar o arquivo: ' + response.statusText);
                }

                return response.text();
            })
            .then(data => {
                infoDisplay.textContent = data; // Exibe o conteúdo no elemento info
            })
            .catch(error => {
                console.error('Erro:', error);
            });
    }

    function loadRegulamento() {
        fetch('/static/regulamento.txt')
            .then(response => {
                console.log('Status da resposta:', response.status); // Log do status da resposta

                if (!response.ok) {
                    throw new Error('Erro ao carregar o arquivo: ' + response.statusText);
                }

                return response.text();
            })
            .then(data => {
                 regulamentoDisplay.textContent = data; // Exibe o conteúdo no elemento regulamento
            })
            .catch(error => {
                console.error('Erro:', error);
            });
    }


    loadInfo(); // Chama a função para carregar o conteúdo ao iniciar
    loadRegulamento();
});