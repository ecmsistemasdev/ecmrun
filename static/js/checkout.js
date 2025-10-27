document.addEventListener('DOMContentLoaded', function() {

    // Inicializar o Mercado Pago
    const mp = new MercadoPago(window.MP_PUBLIC_KEY, {
        locale: 'pt-BR'
    });

    // Gerar device ID
    let deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    console.log('Device ID gerado:', deviceId);

    // Carregar valor do localStorage
    console.log('Valor no localStorage:', localStorage.getItem('valortotal'));
    const storedAmountRaw = localStorage.getItem('valortotal') || '0';
    function normalizeAmount(input) {
      const s = String(input).trim();
      if (!s) return '0';
      const hasComma = s.includes(',');
      const hasDot = s.includes('.');
      if (hasComma && hasDot) {
        // 1.234,56 -> 1234.56
        return s.replace(/\./g, '').replace(',', '.');
      }
      if (hasComma) {
        // 10,50 -> 10.50
        return s.replace(',', '.');
      }
      // Only dot or digits
      return s;
    }
    const amountNumber = parseFloat(normalizeAmount(storedAmountRaw)) || 0;
    const amountElement = document.getElementById('transaction-amount');
    amountElement.textContent = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(amountNumber);

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

    // Valores da inscrição
    const vlinscricao = parseFloat(localStorage.getItem('valoratual') || 0);
    const vltaxa = parseFloat(localStorage.getItem('valortaxa') || 0);
    const totalValue = parseFloat(localStorage.getItem('valortotal') || 0);

    // Inicializar CardForm do Mercado Pago
    console.log('Inicializando CardForm...');
    
    const cardForm = mp.cardForm({
        amount: String(amountNumber.toFixed(2)),
        iframe: true,
        form: {
            id: "payment-form",
            cardNumber: {
                id: "form-checkout__cardNumber",
                placeholder: "Número do cartão",
            },
            expirationDate: {
                id: "form-checkout__expirationDate",
                placeholder: "MM/YY",
            },
            securityCode: {
                id: "form-checkout__securityCode",
                placeholder: "CVV",
            },
            cardholderName: {
                id: "card_holder_name",
                placeholder: "Nome completo",
            },
            installments: {
                id: "installments",
                placeholder: "Parcelas",
            },
            identificationType: {
                id: "doc_type",
            },
            identificationNumber: {
                id: "doc_number",
                placeholder: "Número do documento",
            },
            issuer: {
                id: "issuer",
                placeholder: "Banco emissor",
            },
        },
        callbacks: {
            onFormMounted: error => {
                if (error) {
                    console.error("Erro ao montar CardForm:", error);
                    alert('Erro ao carregar formulário de pagamento. Recarregue a página.');
                    return;
                }
                console.log("CardForm montado com sucesso!");
            },
            onSubmit: event => {
                event.preventDefault();
                console.log('Submit interceptado pelo CardForm');
                handleFormSubmit(event);
            },
            onFetching: (resource) => {
                console.log("Buscando recurso:", resource);
                const submitButton = document.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.textContent = 'Carregando...';
                }
                return () => {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Finalizar Pagamento';
                };
            },
            onCardTokenReceived: (error, token) => {
                if (error) {
                    console.error("Erro ao gerar token:", error);
                    return;
                }
                console.log("Token recebido:", token);
            },
            onPaymentMethodsReceived: (error, paymentMethods) => {
                if (error) {
                    console.error("Erro ao receber métodos de pagamento:", error);
                    return;
                }
                
                console.log("Métodos de pagamento recebidos:", paymentMethods);
                
                // Atualizar ícone da bandeira
                if (paymentMethods && paymentMethods[0]) {
                    const cardBrandIcon = document.getElementById('card-brand-icon');
                    if (paymentMethods[0].secure_thumbnail) {
                        cardBrandIcon.src = paymentMethods[0].secure_thumbnail;
                        cardBrandIcon.style.display = 'block';
                    } else if (paymentMethods[0].thumbnail) {
                        cardBrandIcon.src = paymentMethods[0].thumbnail;
                        cardBrandIcon.style.display = 'block';
                    }
                }
            },
            onInstallmentsReceived: (error, installments) => {
                if (error) {
                    console.error("Erro ao receber parcelas:", error);
                    return;
                }
                console.log("Parcelas recebidas:", installments);
            },
        }
    });

    // Checkbox para usar dados da inscrição
    const checkbox = document.getElementById('same-user-data');
    const cardHolderName = document.getElementById('card_holder_name');
    const docNumber = document.getElementById('doc_number');
    const userEmail = document.getElementById('user_email');
    const docType = document.getElementById('doc_type');

    if (checkbox) {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                const storedName = localStorage.getItem('user_name');
                const storedCPF = localStorage.getItem('user_cpf');
                const storedEmail = localStorage.getItem('user_email');

                if (storedName && storedCPF && storedEmail) {
                    cardHolderName.value = storedName.toUpperCase();
                    docNumber.value = storedCPF;
                    userEmail.value = storedEmail;
                    docType.value = 'CPF';
                    
                    // Disparar eventos
                    cardHolderName.dispatchEvent(new Event('input', { bubbles: true }));
                    docNumber.dispatchEvent(new Event('input', { bubbles: true }));
                    userEmail.dispatchEvent(new Event('input', { bubbles: true }));
                    docType.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    alert('Dados da inscrição não encontrados. Por favor, preencha os campos manualmente.');
                    this.checked = false;
                }
            } else {
                cardHolderName.value = '';
                docNumber.value = '';
                userEmail.value = '';
            }
        });
    }

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

    // Validação do nome completo
    if (cardHolderName) {
        cardHolderName.addEventListener('blur', function(e) {
            const fullName = e.target.value.trim();
            const nameParts = fullName.split(' ').filter(part => part.length > 0);
            
            if (nameParts.length < 2) {
                e.target.setCustomValidity('Por favor, insira nome e sobrenome completos');
            } else {
                e.target.setCustomValidity('');
            }
        });
    }

    // Função para redirecionar ao comprovante
    async function redirectToReceipt(paymentId) {
        try {
            console.log('Atualizando ID do pagamento...');
            
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
                console.log('Pagamento verificado e aprovado. Redirecionando...');
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
    async function handleFormSubmit(event) {
        event.preventDefault();
        
        const submitButton = document.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.textContent;
        
        // Mostrar modal de processamento
        const processingModal = document.getElementById('processing-modal');
        if (processingModal) {
            processingModal.style.display = 'flex';
        }
        
        try {
            submitButton.textContent = 'Processando...';
            submitButton.disabled = true;
            
            // Validar nome completo
            const fullName = cardHolderName.value.trim();
            const nameParts = fullName.split(' ').filter(part => part.length > 0);
            
            if (nameParts.length < 2) {
                throw new Error('Por favor, insira nome e sobrenome completos');
            }
            
            const firstName = nameParts[0];
            const lastName = nameParts.slice(1).join(' ');
            
            // Buscar dados do pagador
            const docNumberValue = docNumber.value.replace(/\D/g, '');
            const docTypeValue = docType.value;
            
            // Validar documento
            if (docTypeValue === 'CPF' && !validateCPF(docNumberValue)) {
                throw new Error('CPF inválido');
            } else if (docTypeValue === 'CNPJ' && !validateCNPJ(docNumberValue)) {
                throw new Error('CNPJ inválido');
            }
            
            console.log('Obtendo dados do CardForm...');
            
            // Obter dados do formulário através do CardForm
            const formData = await cardForm.getCardFormData();
            
            console.log('Dados do CardForm:', formData);
            
            if (!formData || !formData.token) {
                throw new Error('Não foi possível gerar o token do cartão. Verifique os dados do cartão.');
            }
            
            console.log('Token gerado com sucesso');
            
            // Dados do usuário
            const userData = {
                CPF: docNumberValue,
                valor_atual: vlinscricao,
                valor_taxa: vltaxa,
                valor_total: totalValue,
                device_id: deviceId,
                inscrito_cpf: localStorage.getItem('user_cpf'),
                inscrito_name: localStorage.getItem('user_name'),
                inscrito_email: localStorage.getItem('user_email'),
                id_evento: localStorage.getItem('id_evento')
            };
            
            console.log('Preparando dados de pagamento...');
            
            // Estrutura de pagamento
            const paymentData = {
                transaction_amount: Number(amountNumber.toFixed(2)),
                token: formData.token,
                description: "ECM RUN Inscrição",
                installments: Number(formData.installments),
                payment_method_id: formData.paymentMethodId,
                issuer_id: formData.issuerId,
                payer: {
                    email: formData.cardholderEmail || userEmail.value,
                    identification: {
                        type: docTypeValue,
                        number: docNumberValue
                    },
                    first_name: firstName,
                    last_name: lastName
                },
                ...userData
            };

            console.log('Enviando pagamento para o servidor...');
            
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

            console.log('Pagamento processado com sucesso:', responseData);
            
            if (responseData.status === "approved") {
                alert('Pagamento aprovado com sucesso!');
                await redirectToReceipt(responseData.id);
            } else {
                let message = 'Pagamento não foi aprovado.';
                if (responseData.status === 'pending') {
                    message = 'Pagamento está pendente de aprovação.';
                } else if (responseData.status === 'rejected') {
                    message = 'Pagamento foi rejeitado.';
                }
                
                if (responseData.status_detail) {
                    message += ` Motivo: ${responseData.status_detail}`;
                }
                
                alert(message);
            }

        } catch (error) {
            console.error('Erro detalhado:', error);
            alert(`Erro ao processar pagamento: ${error.message}`);
        } finally {
            submitButton.textContent = originalButtonText;
            submitButton.disabled = false;
            
            // Esconder modal de processamento
            if (processingModal) {
                processingModal.style.display = 'none';
            }
        }
    }
});
