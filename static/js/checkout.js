document.addEventListener('DOMContentLoaded', function() {

    // Inicializar o Mercado Pago
    const mp = new MercadoPago(window.MP_PUBLIC_KEY, {
        locale: 'pt-BR'
    });

    // Carregar valor do localStorage
    console.log('Valor no localStorage:', localStorage.getItem('valortotal'));
    const storedAmount = localStorage.getItem('valortotal') || '0.00';
    const amountElement = document.getElementById('transaction-amount');
    amountElement.textContent = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(storedAmount);
    
    // Recuperar e exibir o ID do evento
    const idEvento = localStorage.getItem('id_evento');
    console.log('ID do Evento recuperado:', idEvento);

    // Validar se o ID do evento existe
    if (!idEvento) {
        console.error('ID do evento não encontrado no localStorage');
        alert('Erro: ID do evento não encontrado. Redirecionando para a página anterior.');
        window.history.back();
        return;
    }

    // Adicionar listener para o checkbox
    const vlinscricao = parseFloat(localStorage.getItem('valoratual') || 0);
    const vltaxa = parseFloat(localStorage.getItem('valortaxa') || 0);
    const totalValue = parseFloat(localStorage.getItem('valortotal') || 0);

    const checkbox = document.getElementById('same-user-data');
    const cardHolderName = document.getElementById('card_holder_name');
    const docNumber = document.getElementById('doc_number');
    const userEmail = document.getElementById('user_email');
    const docType = document.getElementById('doc_type');

    checkbox.addEventListener('change', function() {
        if (this.checked) {
            // Preencher com dados do localStorage
            const storedName = localStorage.getItem('user_name');
            const storedCPF = localStorage.getItem('user_cpf');
            const storedEmail = localStorage.getItem('user_email');
            
            console.log('Valor no localStorage:', localStorage.getItem('valortotal'));

            if (storedName && storedCPF && storedEmail) {
                cardHolderName.value = storedName;
                docNumber.value = storedCPF;
                userEmail.value = storedEmail;
                
                // Forçar CPF como tipo de documento
                docType.value = 'CPF';
                
                // Desabilitar campos
                cardHolderName.disabled = true;
                docNumber.disabled = true;
                userEmail.disabled = true;
                docType.disabled = true;
            } else {
                alert('Dados da inscrição não encontrados. Por favor, preencha os campos manualmente.');
                this.checked = false;
            }
        } else {
            // Limpar e habilitar campos
            cardHolderName.value = '';
            docNumber.value = '';
            userEmail.value = '';
            
            cardHolderName.disabled = false;
            docNumber.disabled = false;
            userEmail.disabled = false;
            docType.disabled = false;
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

    // Função para permitir apenas números em campos específicos
    function allowOnlyNumbers(input) {
        input.addEventListener('input', function(e) {
            // Remove todos os caracteres que não são dígitos
            let value = e.target.value.replace(/\D/g, '');
            e.target.value = value;
        });
    }
    
    // Função para CVV (permitir apenas números)
    function setupCVVValidation() {
        const cvvInput = document.getElementById('security-code');
        cvvInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            // Limitar a 4 dígitos (American Express) ou 3 dígitos (outros)
            if (value.length > 4) {
                value = value.slice(0, 4);
            }
            e.target.value = value;
        });
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
        
        // Limitar o tamanho do valor baseado no tipo de documento
        if (docType === 'CPF') {
            value = value.slice(0, 11);
        } else {
            value = value.slice(0, 14);
        }
        
        if (docType === 'CPF') {
            e.target.value = formatCPF(value);
        } else {
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
        // Remover espaços e caracteres não numéricos
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
                    brand: data.id,  // Retorna o ID correto para o Mercado Pago
                    icon: data.icon
                };
            }
        }
        
        return null;
    }

    document.getElementById('installments').addEventListener('change', function(e) {
        const selectedInstallments = e.target.value;
        const bin = document.getElementById('card-number').value.replace(/\s/g, '').substring(0, 6);
        const amount = parseFloat(localStorage.getItem('valortotal'));
        
        if (bin.length >= 6 && !isNaN(amount)) {
            mp.getInstallments({
                amount: String(amount),
                locale: 'pt-BR',
                bin: bin
            }).then((response) => {
                if (response && response.length > 0) {
                    updateTotalAmount(response[0]);
                }
            }).catch(error => {
                console.error('Erro ao atualizar valor com juros:', error);
            });
        }
    });


    // Função para atualizar o valor total com juros
    function updateTotalAmount(installmentData) {
        const amountElement = document.getElementById('transaction-amount');
        const selectedInstallment = document.getElementById('installments').value;
        
        // Encontrar os dados da parcela selecionada
        const selectedOption = installmentData.payer_costs.find(
            cost => cost.installments === parseInt(selectedInstallment)
        );
        
        if (selectedOption) {
            // Calcular o valor total com juros
            const totalWithInterest = selectedOption.total_amount;
            
            // Atualizar o display
            amountElement.textContent = new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(totalWithInterest);
            
            // Atualizar o valor no localStorage para uso posterior
            localStorage.setItem('valorTotalComJuros', totalWithInterest);
        }
    }


    // Função atualizada para obter parcelas
    async function getInstallments(amount, paymentMethodId) {
        try {
            console.log('Calculando parcelas para:', { amount, paymentMethodId });
            
            const response = await mp.getInstallments({
                amount: String(amount),
                locale: 'pt-BR',
                payment_method_id: paymentMethodId,
            });

            console.log('Resposta do getInstallments:', response);

            if (response && response.length > 0) {
                const installmentSelect = document.getElementById('installments');
                installmentSelect.innerHTML = ''; // Limpa as opções existentes

                response[0].payer_costs.forEach((cost) => {
                    const formattedAmount = new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                    }).format(cost.installment_amount);

                    const optionText = cost.recommended_message || 
                        `${cost.installments}x de ${formattedAmount}`;

                    const option = document.createElement('option');
                    option.value = cost.installments;
                    option.textContent = optionText;
                    installmentSelect.appendChild(option);
                });
            } else {
                console.error('Nenhuma opção de parcelamento disponível');
                document.getElementById('installments').innerHTML = '<option value="">Nenhuma parcela disponível</option>';
            }
        } catch (error) {
            console.error('Erro detalhado ao obter parcelas:', error);
            document.getElementById('installments').innerHTML = '<option value="">Erro ao carregar parcelas</option>';
        }
    }

    // Atualização do listener do número do cartão
    document.getElementById('card-number').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/(\d{4})(?=\d)/g, '$1 ');
        e.target.value = value.substring(0, 19);

        const cardNumber = value.replace(/\s/g, '');
        const cardBrandIcon = document.getElementById('card-brand-icon');
        
        if (cardNumber.length >= 6) {
            const cardTypeInfo = getCardType(cardNumber);
            if (cardTypeInfo) {
                // Atualizar ícone da bandeira
                cardBrandIcon.src = cardTypeInfo.icon;
                cardBrandIcon.style.display = 'block';

                // Processar parcelas
                const bin = cardNumber.substring(0, 6);
                const storedAmount = localStorage.getItem('valortotal');
                
                if (storedAmount) {
                    const amount = parseFloat(storedAmount);
                    if (!isNaN(amount)) {
                        mp.getInstallments({
                            amount: String(amount),
                            locale: 'pt-BR',
                            payment_method_id: cardTypeInfo.brand,
                            bin: bin
                        }).then((response) => {
                            console.log('Resposta do getInstallments:', response);
                            if (response && response.length > 0) {
                                const installmentSelect = document.getElementById('installments');
                                installmentSelect.innerHTML = '';

                                response[0].payer_costs.forEach((cost) => {
                                    const formattedAmount = new Intl.NumberFormat('pt-BR', {
                                        style: 'currency',
                                        currency: 'BRL'
                                    }).format(cost.installment_amount);

                                    const optionText = cost.recommended_message || 
                                        `${cost.installments}x de ${formattedAmount}`;

                                    const option = document.createElement('option');
                                    option.value = cost.installments;
                                    option.textContent = optionText;
                                    installmentSelect.appendChild(option);
                                });
                            }
                        }).catch((error) => {
                            console.error('Erro ao obter parcelas:', error);
                            document.getElementById('installments').innerHTML = 
                                '<option value="">Erro ao carregar parcelas</option>';
                        });
                    }
                }
            } else {
                cardBrandIcon.style.display = 'none';
                document.getElementById('installments').innerHTML = 
                    '<option value="">Cartão não reconhecido</option>';
            }
        } else {
            cardBrandIcon.style.display = 'none';
            document.getElementById('installments').innerHTML = 
                '<option value="">Digite mais números do cartão...</option>';
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


    async function redirectToReceipt(paymentId) {
        try {
            console.log('Atualizando ID do pagamento...');
            
            // Primeiro, atualizar o ID do pagamento no banco
            const cpf = localStorage.getItem('user_cpf');
            const idEvento = localStorage.getItem('id_evento');
            
            if (!cpf || !idEvento) {
                throw new Error('CPF ou ID do evento não encontrados');
            }
            
            const updateResponse = await fetch(`/atualiza-idpagamento/${cpf}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    payment_id: paymentId,
                    id_evento: idEvento
                })
            });
            
            if (!updateResponse.ok) {
                throw new Error('Erro ao atualizar ID do pagamento');
            }
            
            const updateData = await updateResponse.json();
            console.log('ID do pagamento atualizado:', updateData);
            
            // Agora verificar o status do pagamento
            console.log('Verificando status do pagamento...');
            
            const verificationResponse = await fetch(`/verificar-pagamento/${paymentId}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!verificationResponse.ok) {
                throw new Error('Erro na verificação do pagamento');
            }
            
            const verificationData = await verificationResponse.json();
            console.log('Resultado da verificação:', verificationData);
            
            if (verificationData.success && verificationData.status === 'approved') {
                console.log('Pagamento verificado e aprovado. Redirecionando para comprovante...');
                window.location.replace(`/comprovante/${paymentId}`);
            } else {
                throw new Error('Pagamento não aprovado ou erro na verificação');
            }
            
        } catch (error) {
            console.error('Erro ao processar pagamento:', error);
            alert('Erro ao processar o pagamento. Por favor, entre em contato com o suporte.');
        }
    }

    // Manipulador do envio do formulário
    document.getElementById('payment-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const vlinscricao = parseFloat(localStorage.getItem('valoratual') || 0);
        const vltaxa = parseFloat(localStorage.getItem('valortaxa') || 0);
        const totalValue = parseFloat(localStorage.getItem('valortotal') || 0);

        try {
            // Display loading state
            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.textContent;
            submitButton.textContent = 'Processando...';
            submitButton.disabled = true;
            
            // Validate fields
            const fullName = document.querySelector('[name="card_holder_name"]').value.trim();
            const nameParts = fullName.split(' ').filter(part => part.length > 0);
            
            if (nameParts.length < 2) {
                throw new Error('Por favor, insira nome e sobrenome completos');
            }
            
            const firstName = nameParts[0];
            const lastName = nameParts.slice(1).join(' ');
            
            // Card validation
            const cardNumber = document.getElementById('card-number').value.replace(/\s/g, '');
            const cardTypeInfo = getCardType(cardNumber);
            
            if (!cardTypeInfo) {
                throw new Error('Cartão não reconhecido. Por favor, verifique o número do cartão');
            }
            
            console.log('Criando token do cartão...');

            // Get data from storage
            const userData = {
                CPF: localStorage.getItem('user_cpf'),
                valor_atual: vlinscricao,
                valor_taxa: vltaxa,
                valor_total: totalValue
            };
            
            console.log('userData: ', userData);

            // Create card token
            const cardFormData = {
                cardNumber: cardNumber,
                cardExpirationMonth: document.getElementById('expiration-date').value.split('/')[0],
                cardExpirationYear: '20' + document.getElementById('expiration-date').value.split('/')[1],
                securityCode: document.getElementById('security-code').value,
                cardholderName: fullName
            };

            console.log('Dados do cartão (sem número completo):', {
                ...cardFormData,
                cardNumber: cardFormData.cardNumber.substring(0, 6) + '******' + cardFormData.cardNumber.slice(-4)
            });
            
            const cardToken = await mp.createCardToken(cardFormData);
            console.log('Token gerado:', cardToken);

            if (!cardToken.id) {
                throw new Error('Não foi possível gerar o token do cartão');
            }

            // Get document info
            const docNumber = document.querySelector('[name="doc_number"]').value.replace(/\D/g, '');
            const docType = document.querySelector('[name="doc_type"]').value;

            // Calculate correct amount
            const finalAmount = Number(parseFloat(localStorage.getItem('valortotal') || 0).toFixed(2));
            const installments = parseInt(document.querySelector('[name="installments"]').value);

            // Create payment data
            const paymentData = {
                transaction_amount: finalAmount,
                token: cardToken.id,
                description: "ECM RUN Inscrição ",
                installments: installments,
                payment_method_id: cardTypeInfo.brand,
                payer: {
                    email: document.querySelector('[name="email"]').value,
                    identification: {
                        type: docType,
                        number: docNumber
                    },
                    first_name: firstName,
                    last_name: lastName
                },
                ...userData
            };

            console.log('Enviando dados para o servidor:', {
                ...paymentData,
                token: '***HIDDEN***' // Hide sensitive token
            });
            
            // Send payment request
            const response = await fetch('/process_payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(paymentData)
            });

            // Parse response
            const responseData = await response.json();
            console.log('Resposta do servidor:', responseData);

            if (!response.ok) {
                // Enhanced error handling
                let errorMessage = 'Erro ao processar pagamento';
                
                if (responseData.error) {
                    errorMessage = responseData.error;
                }
                
                if (responseData.details) {
                    console.error('Detalhes do erro:', responseData.details);
                    
                    // Try to get more readable error message
                    if (typeof responseData.details === 'object' && responseData.details.cause) {
                        errorMessage += `: ${responseData.details.cause[0].description || responseData.details.cause[0].code}`;
                    }
                }
                
                throw new Error(errorMessage);
            }

            // Handle successful response
            console.log('Pagamento processado com sucesso:', responseData);
            
            if (responseData.status === "approved") {
                alert('Pagamento aprovado com sucesso!');
                
                console.log('Payment ID:', responseData.id);
                
                try {
                    // Chama diretamente a função que verifica o pagamento e redireciona
                    await redirectToReceipt(responseData.id);
                } catch (error) {
                    console.error('Erro ao processar redirecionamento:', error);
                    alert('Pagamento aprovado, mas houve um erro no redirecionamento. Por favor, entre em contato com o suporte.');
                }
            }


        } catch (error) {
            console.error('Erro detalhado:', error);
            alert(`Erro ao processar pagamento: ${error.message}`);
        } finally {
            // Reset button state
            const submitButton = document.querySelector('button[type="submit"]');
            submitButton.textContent = 'Finalizar Pagamento';
            submitButton.disabled = false;
        }
    });

    setupCVVValidation();
    
});

