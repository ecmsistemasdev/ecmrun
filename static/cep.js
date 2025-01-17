async function buscarEndereco() {
    const cep = document.getElementById('cep').value;
    const url = `http://192.168.100.16:5000/cadastro_atleta/${cep}`; // Substitua pela URL da sua API

    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Erro ao buscar o CEP');
        }

        const data = await response.json();
        
        // Preencher os campos com os dados retornados
        document.getElementById('rua').value = data.rua;
        document.getElementById('bairro').value = data.bairro;
        document.getElementById('cidade').value = data.cidade;
        document.getElementById('estado').value = data.estado;

    } catch (error) {
        console.error('Erro:', error);
    }
}
