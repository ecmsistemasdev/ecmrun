document.addEventListener('DOMContentLoaded', function() {

    // Inicializar o Mercado Pago
    const mp = new MercadoPago(window.MP_PUBLIC_KEY, {
        locale: 'pt-BR'
    });

    // ID do evento fixo
    const idEvento = 100;

    // Gerar ou recuperar device ID
    let deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    console.log('Device ID:', deviceId);

    // Elementos do DOM
    const amountInput = document.getElementById('transaction-amount-input');
    const amountDisplay = document.getElementById('transaction-amount-display');
    const cardNumberInput = document.getElementById('card-number');
    const installmentsSelect = document.getElementById('installments');
    const cardBrandIcon = document.getElementById('card-brand-icon');

    // Atualizar display do valor
    amountInput.addEventListener('input', function(e) {
        const value = parseFloat(e.target.value) || 0;
        amountDisplay.textContent = new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
        
        // Limpar parcelas quando valor muda
        installmentsSelect.innerHTML = '<option value="">Informe o número do cartão para ver parcelas</option>';
        
        // Se tem valor e cartão, recarregar parcelas
        const cardNumber = cardNumberInput.value.replace(/\D/g, '');
        if (value > 0 && cardNumber.length >= 6) {
            loadInstallments(value, cardNumber);
        }
    });

    // Funções de validação de documentos
    function validateCPF(cpf) {
        cpf = cpf.replace(/\D/g, '');
        if (cpf.length !== 11) return false;
        if (/^(\d)\1{10}$/.test(cpf)) return false;
        
        let sum = 0;
        for (let i = 0; i < 9; i++) {
            sum += parseInt(cpf.charAt(i)) * (10 - i);
        }
        let rev = 11 - (sum % 11);
        if (rev === 10 || rev === 11) rev = 0;
        if (rev !== parseInt(cpf.charAt(9))) return false;
        
        sum = 0;
        for (let i = 0; i < 10; i++) {
            sum += parseInt(cpf.charAt(i)) * (11 - i);
        }
        rev = 11 - (sum % 11);
        if (rev === 10 || rev === 11) rev = 0;
        if (rev !== parseInt(cpf.charAt(10))) return false;
        
        return true;
    }

    function validateCNPJ(cnpj) {
        cnpj = cnpj.replace(/\D/g, '');
        if (cnpj.length !== 14) return false;
        if (/^(\d)\1{13}$/.test(cnpj)) return false;
        
        let size = cnpj.length - 2;
        let numbers = cnpj.substring(0, size);
        let digits = cnpj.substring(size);
        let sum = 0;
        let pos = size - 7;
        
        for (let i = size; i >= 1; i--) {
            sum += numbers.charAt(size - i) * pos--;
            if (pos < 2) pos = 9;
        }
        
        let result = sum % 11 < 2 ? 0 : 11 - sum % 11;
        if (result !== parseInt(digits.charAt(0))) return false;
        
        size = size + 1;
        numbers = cnpj.substring(0, size);
        sum = 0;
        pos = size - 7;
        
        for (let i = size; i >= 1; i--) {
            sum += numbers.charAt(size - i) * pos--;
            if (pos < 2) pos = 9;
        }
        
        result = sum % 11 < 2 ? 0 : 11 - sum % 11;
        if (result !== parseInt(digits.charAt(1))) return false;
        
        return true;
    }

    // Máscaras para documentos
    function formatCPF(value) {
        value = value.slice(0, 11);
        return value
            .replace(/\D/g, '')
            .replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    }

    function formatCNPJ(value) {
        value = value.slice(0, 14);
        return value
            .replace(/\D/g, '')
            .replace(/^(\d{2})(\d)/, '$1.$2')
            .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
            .replace(/\.(\d{3})(\d)/, '.$1/$2')
            .replace(/(\d{4})(\d)/, '$1-$2');
    }

    // Event listener para máscara de documento
    const docNumberInput = document.getElementById('doc_number');
    const docTypeSelect = document.getElementById('doc_type');

    docNumberInput.addEventListener('input', function(e) {
        const docType = docTypeSelect.value;
        let value = e.target.value.replace(/\D/g, '');
        
        if (docType === 'CPF') {
            value = value.slice(0, 11);
            e.target.value = formatCPF(value);
        } else {
            value = value.slice(0, 14);
            e.target.value = formatCNPJ(value);
        }
    });

    docNumberInput.addEventListener('blur', function(e) {
        const docType = docTypeSelect.value;
        const value = e.target.value.replace(/\D/g, '');
        let isValid = false;
        
        if (docType === 'CPF') {
            isValid = validateCPF(value);
        } else {
            isValid = validateCNPJ(value);
        }
        
        if (!isValid) {
            e.target.classList.add('document-error');
            e.target.setCustomValidity(`${docType} inválido`);
        } else {
            e.target.classList.remove('document-error');
            e.target.setCustomValidity('');
        }
    });

    docTypeSelect.addEventListener('change', function() {
        docNumberInput.value = '';
        docNumberInput.classList.remove('document-error');
        docNumberInput.setCustomValidity('');
    });

    // Função para identificar a bandeira do cartão
    function getCardType(cardNumber) {
        cardNumber = cardNumber.replace(/\D/g, '');
        
        const patterns = {
            visa: {
                pattern: /^4/,
                icon: 'https://ecmrun.com.br/static/img/visa.png',
                id: 'visa'
            },
            mastercard: {
                pattern: /^(5[1-5]|2[2-7])/,
                icon: 'https://ecmrun.com.br/static/img/mastercard.png',
                id: 'master'
            },
            amex: {
                pattern: /^3[47]/,
                icon: 'https://ecmrun.com.br/static/img/amex.png',
                id: 'amex'
            },
            elo: {
                pattern: /^(401178|401179|431274|438935|451416|457393|457631|457632|504175|627780|636297|636368|636369|(506699|5067[0-6]\d|50677[0-8])|(50900\d|5090[1-9]\d|509[1-9]\d{2})|65003[1-3]|(65003[5-9]|65004\d|65005[0-1])|(65040[5-9]|6504[1-3]\d)|(65048[5-9]|65049\d|6505[0-2]\d|65053[0-8])|(65054[1-9]|6505[5-8]\d|65059[0-8])|(65070\d|65071[0-8])|65072[0-7]|(65090[1-9]|65091\d|650920)|(65165[2-9]|6516[6-7]\d)|(65500\d|65501\d)|(65502[1-9]|6550[3-4]\d|65505[0-8]))/,
                icon: 'https://ecmrun.com.br/static/img/elo.png',
                id: 'elo'
            },
            hipercard: {
                pattern: /^(606282\d{10}(\d{3})?)|(3841\d{15})/,
                icon: 'https://ecmrun.com.br/static/img/hipercard.png',
                id: 'hipercard'
            },
            diners: {
                pattern: /^3(?:0[0-5]|[68][0-9])[0-9]{11}/,
                icon: 'https://ecmrun.com.br/static/img/diners.png',
                id: 'diners'
            }
        };
        
        for (let [brand, data] of Object.entries(patterns)) {
            if (data.pattern.test(cardNumber)) {
                return {
                    brand: data.id,
                    icon: data.icon
                };
            }
        }
        
        return null;
    }

    // Função para carregar parcelas
    function loadInstallments(amount, cardNumber) {
        const cardTypeInfo = getCardType(cardNumber);
        if (!cardTypeInfo) {
            installmentsSelect.innerHTML = '<option value="">Cartão não reconhecido</option>';
            return;
        }

        const bin = cardNumber.substring(0, 6);
        
        console.log('Carregando parcelas para:', {
            amount: amount,
            bin: bin,
            payment_method_id: cardTypeInfo.brand
        });

        installmentsSelect.innerHTML = '<option value="">Carregando parcelas...</option>';

        mp.getInstallments({
            amount: String(amount),
            locale: 'pt-BR',
            bin: bin,
            payment_method_id: cardTypeInfo.brand
        }).then((response) => {
            console.log('Resposta do getInstallments:', response);
            
            if (response && response.length > 0 && response[0].payer_costs) {
                installmentsSelect.innerHTML = '';
                
                response[0].payer_costs.forEach((cost) => {
                    const formattedAmount = new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                    }).format(cost.installment_amount);

                    let optionText;
                    if (cost.installments === 1) {
                        optionText = `À vista - ${formattedAmount}`;
                    } else {
                        const totalFormatted = new Intl.NumberFormat('pt-BR', {
                            style: 'currency',
                            currency: 'BRL'
                        }).format(cost.total_amount);
                        
                        if (cost.total_amount > amount) {
                            optionText = `${cost.installments}x de ${formattedAmount} (Total: ${totalFormatted})`;
                        } else {
                            optionText = `${cost.installments}x de ${formattedAmount} sem juros`;
                        }
                    }

                    const option = document.createElement('option');
                    option.value = cost.installments;
                    option.textContent = optionText;
                    option.dataset.totalAmount = cost.total_amount;
                    installmentsSelect.appendChild(option);
                });
            } else {
                installmentsSelect.innerHTML = '<option value="">Nenhuma parcela disponível</option>';
            }
        }).catch((error) => {
            console.error('Erro ao obter parcelas:', error);
            installmentsSelect.innerHTML = '<option value="">Erro ao carregar parcelas</option>';
        });
    }

    // Event listener para número do cartão
    cardNumberInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
        e.target.value = value.substring(0, 19);

        const cardNumber = value.replace(/\s/g, '');
        
        if (cardNumber.length >= 6) {
            const cardTypeInfo = getCardType(cardNumber);
            if (cardTypeInfo) {
                cardBrandIcon.src = cardTypeInfo.icon;
                cardBrandIcon.style.display = 'block';

                // Carregar parcelas se tem valor
                const amount = parseFloat(amountInput.value);
                if (amount > 0) {
                    loadInstallments(amount, cardNumber);
                }
            } else {
                cardBrandIcon.style.display = 'none';
                installmentsSelect.innerHTML = '<option value="">Cartão não reconhecido</option>';
            }
        } else {
            cardBrandIcon.style.display = 'none';
            installmentsSelect.innerHTML = '<option value="">Digite mais números do cartão...</option>';
        }
    });

    // Máscara para data de validade
    document.getElementById('expiration-date').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        e.target.value = value.substring(0, 5);
    });

    // Validação do nome completo
    document.querySelector('[name="card_holder_name"]').addEventListener('input', function(e) {
        const fullName = e.target.value.trim();
        const nameParts = fullName.split(' ').filter(part => part.length > 0);
        
        if (nameParts.length < 2) {
            e.target.setCustomValidity('Por favor, insira nome e sobrenome completos');
        } else {
            e.target.setCustomValidity('');
        }
    });

    // Função para limpar formulário
    function clearForm() {
        document.getElementById('payment-form').reset();
        amountDisplay.textContent = 'R$ 0,00';
        cardBrandIcon.style.display = 'none';
        installmentsSelect.innerHTML = '<option value="">Informe o valor e número do cartão primeiro</option>';
        
        // Remover classes de erro
        const errorElements = document.querySelectorAll('.document-error');
        errorElements.forEach(el => {
            el.classList.remove('document-error');
            el.setCustomValidity('');
        });
    }

    // Função para mostrar modal de processamento
    function showProcessingModal() {
        document.getElementById('processing-modal').style.display = 'flex';
    }

    // Função para esconder modal de processamento
    function hideProcessingModal() {
        document.getElementById('processing-modal').style.display = 'none';
    }

    // Manipulador do envio do formulário
    document.getElementById('payment-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const submitButton = document.getElementById('submit-button');
        const originalButtonText = submitButton.textContent;
        
        try {
            // Mostrar modal de processamento
            showProcessingModal();
            submitButton.textContent = 'Processando...';
            submitButton.disabled = true;
            
            // Validar valor
            const amount = parseFloat(amountInput.value);
            if (!amount || amount <= 0) {
                throw new Error('Por favor, informe um valor válido');
            }
            
            // Validar nome completo
            const fullName = document.querySelector('[name="card_holder_name"]').value.trim();
            const nameParts = fullName.split(' ').filter(part => part.length > 0);
            
            if (nameParts.length < 2) {
                throw new Error('Por favor, insira nome e sobrenome completos');
            }
            
            const firstName = nameParts[0];
            const lastName = nameParts.slice(1).join(' ');
            
            // Validar cartão
            const cardNumber = cardNumberInput.value.replace(/\s/g, '');
            const cardTypeInfo = getCardType(cardNumber);
            
            if (!cardTypeInfo) {
                throw new Error('Cartão não reconhecido. Por favor, verifique o número do cartão');
            }
            
            // Validar outros campos
            const expirationDate = document.getElementById('expiration-date').value;
            const securityCode = document.getElementById('security-code').value;
            const email = document.querySelector('[name="email"]').value;
            
            if (!expirationDate || expirationDate.length !== 5) {
                throw new Error('Data de validade inválida. Use o formato MM/AA');
            }
            
            if (!securityCode || securityCode.length < 3) {
                throw new Error('Código de segurança inválido');
            }
            
            if (!email) {
                throw new Error('Email é obrigatório');
            }

            // Criar token do cartão
            const cardFormData = {
                cardNumber: cardNumber,
                cardExpirationMonth: expirationDate.split('/')[0],
                cardExpirationYear: '20' + expirationDate.split('/')[1],
                securityCode: securityCode,
                cardholderName: fullName
            };

            console.log('Criando token do cartão...');
            const cardToken = await mp.createCardToken(cardFormData);
            
            if (!cardToken.id) {
                throw new Error('Não foi possível gerar o token do cartão');
            }

            // Preparar dados do pagamento
            const docNumber = document.querySelector('[name="doc_number"]').value.replace(/\D/g, '');
            const docType = document.querySelector('[name="doc_type"]').value;
            const installments = parseInt(document.querySelector('[name="installments"]').value);

            const paymentData = {
                transaction_amount: amount,
                token: cardToken.id,
                description: "ECM RUN Cobrança",
                installments: installments,
                payment_method_id: cardTypeInfo.brand,
                payer: {
                    email: email,
                    identification: {
                        type: docType,
                        number: docNumber
                    },
                    first_name: firstName,
                    last_name: lastName
                },
                // Dados extras
                CPF: docNumber,
                valor_atual: amount,
                valor_taxa: 0,
                valor_total: amount,
                device_id: deviceId,
                id_evento: idEvento
            };

            console.log('Enviando dados para o servidor...');
            
            // Enviar pagamento
            const response = await fetch('/process_payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(paymentData)
            });

            const responseData = await response.json();
            console.log('Resposta do servidor:', responseData);

            if (!response.ok) {
                let errorMessage = 'Erro ao processar pagamento';
                
                if (responseData.error) {
                    errorMessage = responseData.error;
                }
                
                if (responseData.details) {
                    console.error('Detalhes do erro:', responseData.details);
                    
                    if (typeof responseData.details === 'object' && responseData.details.cause) {
                        errorMessage += `: ${responseData.details.cause[0].description || responseData.details.cause[0].code}`;
                    }
                }
                
                throw new Error(errorMessage);
            }

            // Tratar resposta
            if (responseData.status === "approved") {
                alert('Pagamento aprovado com sucesso!\n' +
                      `ID do Pagamento: ${responseData.id}\n` +
                      `Valor: ${new Intl.NumberFormat('pt-BR', {
                          style: 'currency',
                          currency: 'BRL'
                      }).format(amount)}`);
                clearForm();
            } else {
                let message = 'Pagamento não foi aprovado.';
                if (responseData.status === 'pending') {
                    message = 'Pagamento está pendente de aprovação.';
                } else if (responseData.status === 'rejected') {
                    message = 'Pagamento foi rejeitado.';
                }
                
                if (responseData.status_detail) {
                    message += `\nMotivo: ${responseData.status_detail}`;
                }
                
                alert(message);
            }

        } catch (error) {
            console.error('Erro detalhado:', error);
            alert(`Erro ao processar pagamento: ${error.message}`);
        } finally {
            // Resetar estado do botão e esconder modal
            hideProcessingModal();
            submitButton.textContent = originalButtonText;
            submitButton.disabled = false;
        }
    });
});