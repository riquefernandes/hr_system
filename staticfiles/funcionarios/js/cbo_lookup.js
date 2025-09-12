// funcionarios/static/funcionarios/js/cbo_lookup.js
document.addEventListener('DOMContentLoaded', function () {
    const cboInput = document.getElementById('id_cbo');
    const nomeInput = document.getElementById('id_nome');

    if (cboInput && nomeInput) {
        cboInput.addEventListener('blur', function () {
            const cboCode = this.value.replace(/[^0-9]/g, '');

            if (cboCode.length > 0) {
                fetch(`https://brasilapi.com.br/api/cbo/v1/${cboCode}`)
                    .then((response) => {
                        if (!response.ok) {
                            throw new Error('CBO não encontrado');
                        }
                        return response.json();
                    })
                    .then((data) => {
                        if (data && data.ocupacao) {
                            nomeInput.value = data.ocupacao;
                        } else {
                            alert('Código CBO não encontrado ou inválido.');
                        }
                    })
                    .catch((error) => {
                        console.error('Erro ao buscar CBO:', error);
                        alert('Código CBO não encontrado ou inválido.');
                    });
            }
        });
    }
});
