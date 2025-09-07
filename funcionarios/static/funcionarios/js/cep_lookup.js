console.log('Pista 1: Arquivo cep_lookup.js carregado com sucesso!');

document.addEventListener('DOMContentLoaded', function() {
    console.log('Pista 2: DOM carregado. Procurando pelo campo do CEP...');

    const cepInput = document.getElementById('id_cep');
    
    if (cepInput) {
        console.log('Pista 3: Campo com id="id_cep" ENCONTRADO!', cepInput);
        
        cepInput.addEventListener('blur', function() {
            console.log('Pista 4: Evento BLUR disparado! O usuário saiu do campo CEP.');
            
            const cep = this.value.replace(/\D/g, '');

            if (cep.length === 8) {
                console.log('CEP válido, buscando na API...');
                fetch(`https://viacep.com.br/ws/${cep}/json/`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.erro) {
                            console.log('API retornou dados:', data);
                            document.getElementById('id_rua').value = data.logradouro;
                            document.getElementById('id_bairro').value = data.bairro;
                            document.getElementById('id_cidade').value = data.localidade;
                            document.getElementById('id_estado').value = data.uf;
                        } else {
                            console.log('API retornou um erro: CEP não encontrado.');
                            alert('CEP não encontrado.');
                        }
                    })
                    .catch(error => console.error('Erro na chamada da API:', error));
            }
        });
    } else {
        console.error('ERRO CRÍTICO: Campo com id="id_cep" NÃO foi encontrado no DOM.');
    }
});