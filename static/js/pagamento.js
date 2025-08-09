document.addEventListener('DOMContentLoaded', function() {
    let paymentId = null;
    let checkInterval = null;
    const VERIFICATION_TIMEOUT = 10 * 60 * 1000;
    let isRedirecting = false;
    let retryCount = 0;
    const MAX_RETRIES = 3;

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

    const PIX_EXPIRATION_TIME = 30 * 60; // 30 minutos em segundos
    let remainingTime = PIX_EXPIRATION_TIME;
    let countdownInterval;

    const environments = {
        development: {
            baseURL: 'http://192.168.0.89:5000'
        },
        production: {
            baseURL: 'https://ecmrun.com.br'
        }
    };

    const currentEnv = window.location.hostname === 'localhost' ||
                    window.location.hostname.includes('192.168') ?
                    'development' : 'production';

    const baseURL = environments[currentEnv].baseURL;

    const vlinscricao = parseFloat(localStorage.getItem('valoratual') || 0);
    const vltaxa = parseFloat(localStorage.getItem('valortaxa') || 0);
    const totalValue = parseFloat(localStorage.getItem('valortotal') || 0);
    console.info('Valor pag',totalValue)

    // Função para formatar moeda
    function formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }

    // Função para criar e iniciar o timer regressivo CORRIGIDA
    function startCountdownTimer(startFromFull = true) {
        // Remove timer existente se houver
        const existingTimer = document.getElementById('pixCountdown');
        if (existingTimer) {
            existingTimer.remove();
        }

        // Para o interval anterior se existir
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }

        // Define o tempo inicial
        if (startFromFull) {
            remainingTime = PIX_EXPIRATION_TIME;
        }

        // Cria o elemento HTML do timer flutuante
        const timerElement = document.createElement('div');
        timerElement.id = 'pixCountdown';
        timerElement.className = 'timer-container';

        const timerTitle = document.createElement('div');
        timerTitle.className = 'countdown-title';
        timerTitle.innerHTML = 'Tempo p/ pagamento';

        const timerDisplay = document.createElement('div');
        timerDisplay.className = 'countdown-display';
        timerDisplay.id = 'countdownDisplay';

        timerElement.appendChild(timerTitle);
        timerElement.appendChild(timerDisplay);

        // Adiciona ao body para ficar flutuante
        document.body.appendChild(timerElement);

        // Função para atualizar o timer
        function updateTimer() {
            if (remainingTime <= 0) {
                clearInterval(countdownInterval);
                document.getElementById('countdownDisplay').innerHTML = '00:00';
                document.getElementById('pixCountdown').classList.add('expired');

                // Exibe mensagem de expiração
                const expirationMsg = document.createElement('div');
                expirationMsg.className = 'expiration-message';
                expirationMsg.innerHTML = 'O tempo para pagamento expirou. <button class="button refresh-button" onclick="window.location.reload()">Gerar novo QR Code</button>';

                const qrContainer = document.getElementById('qrContainer');
                if (qrContainer) {
                    qrContainer.classList.add('expired');
                    qrContainer.appendChild(expirationMsg);
                }

                return;
            }

            const minutes = Math.floor(remainingTime / 60);
            const seconds = remainingTime % 60;

            // Formata o tempo com zeros à esquerda quando necessário
            const formattedMinutes = minutes < 10 ? `0${minutes}` : minutes;
            const formattedSeconds = seconds < 10 ? `0${seconds}` : seconds;

            // Atualiza o display
            const countdownDisplay = document.getElementById('countdownDisplay');
            if (countdownDisplay) {
                countdownDisplay.innerHTML = `${formattedMinutes}:${formattedSeconds}`;
            }

            // Adiciona classe de alerta quando restar menos de 5 minutos
            const timerContainer = document.getElementById('pixCountdown');
            if (remainingTime <= 300 && timerContainer) {
                timerContainer.classList.add('warning');
            }

            // Decrementa o tempo restante
            remainingTime--;
        }

        // Inicia o timer imediatamente e depois a cada segundo
        updateTimer();
        countdownInterval = setInterval(updateTimer, 1000);

        // Salva o horário de início para recuperação apenas se for um timer novo
        if (startFromFull) {
            localStorage.setItem('pixTimerStart', Date.now().toString());
            localStorage.setItem('pixExpirationDuration', PIX_EXPIRATION_TIME.toString());
        }
    }

    // Função para recuperar o timer existente CORRIGIDA
    function recoverCountdownTimer() {
        const timerStart = localStorage.getItem('pixTimerStart');
        const expirationDuration = localStorage.getItem('pixExpirationDuration');

        if (timerStart && expirationDuration) {
            const elapsed = Math.floor((Date.now() - parseInt(timerStart)) / 1000);
            const totalDuration = parseInt(expirationDuration);

            remainingTime = totalDuration - elapsed;

            if (remainingTime > 0) {
                console.log(`Recuperando timer com ${remainingTime} segundos restantes`);
                startCountdownTimer(false); // Não reinicia do tempo total
                return true;
            } else {
                console.log('Timer expirado, limpando dados');
                localStorage.removeItem('pixTimerStart');
                localStorage.removeItem('pixExpirationDuration');
            }
        }

        return false;
    }

    // Função para limpar o timer quando o pagamento for concluído
    function clearCountdownTimer() {
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }

        const timerElement = document.getElementById('pixCountdown');
        if (timerElement) {
            timerElement.remove();
        }

        localStorage.removeItem('pixTimerStart');
        localStorage.removeItem('pixExpirationDuration');
    }

    // Função para persistir dados do pagamento com verificação
    function persistPaymentData(data) {
        if (!data) return false;

        try {
            const paymentData = {
                paymentId: data.payment_id,
                qrCode: data.qr_code,
                qrCodeBase64: data.qr_code_base64,
                timestamp: Date.now()
            };

            // Verifica se todos os dados necessários estão presentes
            if (!paymentData.paymentId || !paymentData.qrCode || !paymentData.qrCodeBase64) {
                console.error('Dados incompletos para persistência');
                return false;
            }

            sessionStorage.setItem('paymentData', JSON.stringify(paymentData));
            localStorage.setItem('lastPaymentId', data.payment_id); // Backup adicional
            return true;
        } catch (error) {
            console.error('Erro ao persistir dados:', error);
            return false;
        }
    }

    // Função para recuperar dados do pagamento com validação
    function getPersistedPaymentData() {
        try {
            const sessionData = sessionStorage.getItem('paymentData');
            if (sessionData) {
                const data = JSON.parse(sessionData);
                // Verifica se os dados são válidos e não muito antigos (menos de 15 minutos)
                if (data && data.timestamp && (Date.now() - data.timestamp) < 900000) {
                    return data;
                }
            }


            // Se não encontrou no sessionStorage, tenta recuperar o ID do localStorage
            const lastPaymentId = localStorage.getItem('lastPaymentId');
            if (lastPaymentId) {
                return { paymentId: lastPaymentId };
            }

            return null;
        } catch (error) {
            console.error('Erro ao recuperar dados persistidos:', error);
            return null;
        }
    }

    function redirectToReceipt(paymentId) {
        try {
            console.log('Iniciando redirecionamento para comprovante:', paymentId);

            // Limpa o timer antes de redirecionar
            clearCountdownTimer();

            // Para todas as verificações
            if (checkInterval) {
                clearInterval(checkInterval);
            }

            // Limpa dados do pagamento antes do redirecionamento
            sessionStorage.removeItem('paymentData');
            localStorage.removeItem('lastPaymentId');

            // Remove o listener de visibilidade
            document.removeEventListener('visibilitychange', handleVisibilityChange);

            // Construir a URL correta
            const redirectUrl = `${baseURL}/comprovante/${paymentId}`;
            console.log('Redirecionando para:', redirectUrl);

            // Usar replace para não permitir voltar
            window.location.replace(redirectUrl);

        } catch (error) {
            console.error('Erro ao redirecionar:', error);
            // Fallback: tenta redirecionar mesmo com erro
            try {
                window.location.href = `/comprovante/${paymentId}`;
            } catch (fallbackError) {
                console.error('Erro no fallback de redirecionamento:', fallbackError);
                alert('Pagamento confirmado! Por favor, recarregue a página e acesse "Minhas Inscrições" para ver o comprovante.');
            }
        }
    }

    // Adicione esta função que estava faltando
    function clearPaymentRelatedLocalStorage() {
        sessionStorage.removeItem('paymentData');
        localStorage.removeItem('lastPaymentId');
    }

    // Função para recuperar QR Code CORRIGIDA
    async function recoverQRCode(paymentId) {
        try {
            console.log('Tentando recuperar QR Code para:', paymentId);

            const response = await fetch(`${baseURL}/recuperar-qrcode/${paymentId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.error('Erro na resposta da recuperação:', response.status, response.statusText);
                return null;
            }

            const data = await response.json();
            console.log('Dados recuperados:', data);

            if (data.success && data.qr_code && data.qr_code_base64) {
                console.log('QR Code recuperado com sucesso');
                return data;
            } else {
                console.error('Dados do QR Code incompletos na recuperação:', data);
                return null;
            }
        } catch (error) {
            console.error('Erro ao recuperar QR Code:', error);
            return null;
        }
    }

    // Função para exibir QR Code com validação e atualização do ID
    function displayQRCode(qrCodeBase64, qrCodeText, isRecovered = false) {
        if (!qrCodeBase64 || !qrCodeText) {
            throw new Error('Dados do QR Code inválidos');
        }

        const qrContainer = document.getElementById('qrContainer');
        const loadingContainer = document.getElementById('loadingContainer');
        const qrCode = document.getElementById('qrCode');
        const pixKey = document.getElementById('pixKey');
        const totalAmount = document.getElementById('totalAmount');

        // Garante que o valor total seja exibido
        const vlinscricao = parseFloat(localStorage.getItem('valoratual') || 0);
        const vltaxa = parseFloat(localStorage.getItem('valortaxa') || 0);
        const totalValue = parseFloat(localStorage.getItem('valortotal') || 0);
        
        totalAmount.textContent = formatCurrency(totalValue);

        qrCode.src = `data:image/png;base64,${qrCodeBase64}`;
        pixKey.textContent = qrCodeText;
        
        loadingContainer.classList.add('hidden');
        qrContainer.classList.remove('hidden');

        // Inicia o timer apenas se não conseguir recuperar um existente
        if (!recoverCountdownTimer()) {
            console.log('Iniciando novo timer de 30 minutos');
            startCountdownTimer(true); // Inicia do tempo total
        }
    }


    function validatePaymentData() {
        // Check if all required localStorage data is present
        const requiredFields = [
            'user_name', 'user_email', 'user_cpf',
            'categoria', 'valoratual', 'valortaxa', 'valortotal'
        ];

        const missingFields = [];
        requiredFields.forEach(field => {
            const value = localStorage.getItem(field);
            if (!value) {
                missingFields.push(field);
            }
        });

        if (missingFields.length > 0) {
            console.error('Missing required fields:', missingFields);
            return false;
        }

        // Validate numeric values
        const valorAtual = parseFloat(localStorage.getItem('valoratual') || '0');
        const valorTaxa = parseFloat(localStorage.getItem('valortaxa') || '0');
        const valorTotal = parseFloat(localStorage.getItem('valortotal') || '0');

        if (isNaN(valorAtual) || isNaN(valorTaxa) || isNaN(valorTotal)) {
            console.error('Invalid numeric values:', {
                valorAtual,
                valorTaxa,
                valorTotal
            });
            return false;
        }

        return true;
    }

    // Função para atualizar o ID do pagamento na base de dados CORRIGIDA
    async function atualizarIdPagamento(paymentId) {
        try {
            const cpf = localStorage.getItem('user_cpf');
            const idEvento = localStorage.getItem('id_evento');

            if (!cpf || !idEvento) {
                console.error('Dados necessários não encontrados:', { cpf, idEvento });
                return false;
            }

            console.log('Atualizando ID do pagamento:', {
                cpf: cpf,
                payment_id: paymentId,
                id_evento: idEvento
            });

            const response = await fetch(`${baseURL}/atualiza-idpagamento/${cpf}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    payment_id: paymentId,
                    id_evento: idEvento
                })
            });

            if (!response.ok) {
                console.error('Erro na resposta da atualização:', response.status);
                return false;
            }

            const result = await response.json();

            if (result.success) {
                console.log('ID do pagamento atualizado com sucesso:', result);
                return true;
            } else {
                console.error('Erro ao atualizar ID do pagamento:', result.message);
                return false;
            }

        } catch (error) {
            console.error('Erro na requisição de atualização do ID pagamento:', error);
            return false;
        }
    }

    // Função principal para gerar pagamento PIX com retry CORRIGIDA
    async function generatePixPayment(totalValue, isRetry = false) {
        try {
            // VERIFICA SE JÁ EXISTE UM PAYMENT VÁLIDO ANTES DE GERAR NOVO
            if (!isRetry) {
                const persistedData = getPersistedPaymentData();
                if (persistedData && persistedData.paymentId) {
                    console.log('Payment já existe, não gerando novo:', persistedData.paymentId);
                    return;
                }
            }

            if (isRetry && retryCount >= MAX_RETRIES) {
                throw new Error('Número máximo de tentativas excedido');
            }

            // Validate data before sending
            if (!validatePaymentData()) {
                throw new Error('Dados de pagamento inválidos ou incompletos');
            }

            // Parse values safely ensuring they're numbers
            const vlinscricao = parseFloat(localStorage.getItem('valoratual') || '0');
            const vltaxa = parseFloat(localStorage.getItem('valortaxa') || '0');
            const totalValue = parseFloat(localStorage.getItem('valortotal') || '0');

            console.log('Valores sendo enviados:', {
                vlinscricao,
                vltaxa,
                totalValue,
                vlinscricaoType: typeof vlinscricao,
                vltaxaType: typeof vltaxa,
                totalValueType: typeof totalValue
            });

            const userData = {
                idatleta: localStorage.getItem('user_idatleta'),
                nome: localStorage.getItem('user_name'),
                email: localStorage.getItem('user_email'),
                cpf: localStorage.getItem('user_cpf')
            };

            if (!userData.email || !userData.cpf || !totalValue) {
                throw new Error('Dados incompletos para geração do PIX');
            }

            const requestData = {
                valor_atual: vlinscricao,
                valor_taxa: vltaxa,
                valor_total: totalValue,
                ...userData
            };

            console.log('GERANDO NOVO PAYMENT PIX:', requestData);

            const response = await fetch(`${baseURL}/gerar-pix`, {
                    method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const responseData = await response.json();
            console.log('Resposta do servidor:', responseData);

            if (!response.ok) {
                throw new Error(responseData.message || `Erro HTTP: ${response.status}`);
            }

            // Verifica se tem os dados necessários
            if (!responseData.qr_code || !responseData.qr_code_base64) {
                throw new Error('Dados do QR Code incompletos na resposta');
            }

            if (responseData.qr_code && responseData.qr_code_base64) {
                console.log('NOVO PAYMENT GERADO COM SUCESSO:', responseData.payment_id);
                persistPaymentData(responseData);
                displayQRCode(responseData.qr_code_base64, responseData.qr_code, false);

                if (responseData.payment_id) {
                    // CORREÇÃO: Atualizar ID do pagamento ANTES de iniciar verificação
                    console.log('Atualizando ID do pagamento na base de dados:', responseData.payment_id);
                    try {
                        const updateSuccess = await atualizarIdPagamento(responseData.payment_id);
                        if (updateSuccess) {
                            console.log('ID do pagamento atualizado com sucesso na base de dados');
                        } else {
                            console.warn('Falha ao atualizar ID do pagamento na base de dados, mas continuando...');
                        }
                    } catch (error) {
                        console.error('Erro ao atualizar ID do pagamento:', error);
                    }
                    
                    await startPaymentVerification(responseData.payment_id);
                }
            }

        } catch (error) {
            console.error('Erro ao gerar PIX:', error);

            if (!isRetry) {
                // Só tenta retry se realmente não tem nenhum payment válido
                const persistedData = getPersistedPaymentData();
                if (!persistedData || !persistedData.paymentId) {
                    retryCount++;
                    await generatePixPayment(totalValue, true);
                }
            } else {
                document.getElementById('loadingContainer').innerHTML = `
                    <p>Erro ao gerar QR Code PIX. Por favor, tente novamente em alguns instantes.</p>
                    <button class="button" onclick="window.location.reload()">Tentar novamente</button>
                `;
            }
        }
    }


    // Função para verificar pagamento - VERSÃO CORRIGIDA
    async function startPaymentVerification(paymentId) {
        if (checkInterval) {
            clearInterval(checkInterval);
        }

        let startTime = Date.now();
        let consecutiveErrors = 0;
        const MAX_CONSECUTIVE_ERRORS = 3;

        const checkPayment = async () => {
            if (isRedirecting) return;

            try {
                if (Date.now() - startTime > VERIFICATION_TIMEOUT) {
                    clearInterval(checkInterval);
                    console.log('Tempo de verificação expirado');
                    // Não exibe alert automaticamente, deixa o usuário decidir
                    return;
                }

                console.log(`Verificando pagamento ${paymentId}...`);

                const response = await fetch(`${baseURL}/verificar-pagamento/${paymentId}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Resposta da verificação:', data);

                // Reset contador de erros em caso de sucesso
                consecutiveErrors = 0;

                if (data.success && data.status === 'approved' && !isRedirecting) {
                    console.log('Pagamento aprovado! Redirecionando...');
                    isRedirecting = true;
                    clearInterval(checkInterval);

                    // Remove event listeners
                    document.removeEventListener('visibilitychange', handleVisibilityChange);

                    // Pequeno delay para garantir que o processamento foi concluído
                    setTimeout(() => {
                        redirectToReceipt(paymentId);
                    }, 1000);

                } else if (data.status === 'pending' || data.status === 'in_process') {
                    console.log(`Status do pagamento: ${data.status} - continuando verificação...`);
                } else if (data.status === 'cancelled' || data.status === 'rejected') {
                    console.log(`Pagamento ${data.status}`);
                    clearInterval(checkInterval);
                    alert(`Pagamento ${data.status === 'cancelled' ? 'cancelado' : 'rejeitado'}. Por favor, tente novamente.`);
                }

            } catch (error) {
                consecutiveErrors++;
                console.error(`Erro ao verificar pagamento (tentativa ${consecutiveErrors}):`, error);

                if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
                    clearInterval(checkInterval);
                    console.error('Muitos erros consecutivos, parando verificação automática');
                }
            }
        };

        // Primeira verificação imediata
        await checkPayment();

        if (!isRedirecting) {
            // Verifica a cada 3 segundos (mais frequente para melhor UX)
            checkInterval = setInterval(checkPayment, 3000);
        }
    }

    // Função para lidar com mudanças de visibilidade da página
    function handleVisibilityChange() {
        if (document.visibilityState === 'visible') {
            const persistedData = getPersistedPaymentData();
            if (persistedData && persistedData.paymentId && !isRedirecting) {
                console.log('Página voltou a ficar visível, retomando verificação');
                startPaymentVerification(persistedData.paymentId);
            }
        }
    }

    // Inicialização da página CORRIGIDA - EVITA MÚLTIPLOS PAYMENTS
    async function initializePagamento() {
        try {
            const vlinscricao = parseFloat(localStorage.getItem('valoratual') || 0);
            const vltaxa = parseFloat(localStorage.getItem('valortaxa') || 0);
            const totalValue = parseFloat(localStorage.getItem('valortotal') || 0);

            document.getElementById('totalAmount').textContent = formatCurrency(totalValue);

            // PRIMEIRA PRIORIDADE: Tentar recuperar dados persistidos válidos
            const persistedData = getPersistedPaymentData();

            if (persistedData && persistedData.paymentId) {
                console.log('Dados persistidos encontrados, verificando validade...', persistedData);

                // Se tem QR code completo e é recente (menos de 15 minutos)
                if (persistedData.qrCodeBase64 && persistedData.qrCode &&
                    persistedData.timestamp && (Date.now() - persistedData.timestamp) < 900000) {

                    console.log('Usando dados persistidos completos e válidos');
                    displayQRCode(persistedData.qrCodeBase64, persistedData.qrCode, true);
                    await startPaymentVerification(persistedData.paymentId);
                    return; // PARA AQUI - NÃO GERA NOVO PAYMENT
                }

                // Se tem apenas paymentId, tenta recuperar o QR code
                console.log('Tentando recuperar QR Code para payment existente:', persistedData.paymentId);
                const recoveredData = await recoverQRCode(persistedData.paymentId);

                if (recoveredData && recoveredData.qr_code_base64) {
                    console.log('QR Code recuperado com sucesso');
                    // Atualiza os dados persistidos com o QR code recuperado
                    const updatedData = {
                        ...persistedData,
                        qrCode: recoveredData.qr_code,
                        qrCodeBase64: recoveredData.qr_code_base64,
                        timestamp: Date.now()
                    };
                    persistPaymentData(updatedData);

                    // CORREÇÃO: Garantir que o ID seja atualizado também na recuperação
                    try {
                        console.log('Garantindo atualização do ID para pagamento recuperado');
                        await atualizarIdPagamento(persistedData.paymentId);
                    } catch (error) {
                        console.error('Erro ao atualizar ID na recuperação:', error);
                    }

                    displayQRCode(recoveredData.qr_code_base64, recoveredData.qr_code, true);
                    await startPaymentVerification(persistedData.paymentId);
                    return; // PARA AQUI - NÃO GERA NOVO PAYMENT
                }

                // Se chegou até aqui, o payment existe mas não conseguiu recuperar o QR
                console.log('Payment existe mas QR code expirado/indisponível');
            }

            // ÚLTIMA OPÇÃO: Só gera novo payment se realmente não existe nenhum válido
            console.log('Nenhum pagamento válido encontrado, gerando novo...');
            await generatePixPayment(totalValue);

        } catch (error) {
            console.error('Erro na inicialização:', error);
            // Só mostra erro se realmente não conseguir recuperar nada
            const persistedData = getPersistedPaymentData();
            if (!persistedData || !persistedData.paymentId) {
                alert('Erro ao inicializar o pagamento. Por favor, tente novamente.');
            }
        }
    }

    // Função para copiar chave PIX
    window.copyPixKey = function() {
        const pixKey = document.getElementById('pixKey').textContent;
        if (!pixKey) {
            alert('Chave PIX não disponível no momento. Por favor, aguarde o carregamento ou recarregue a página.');
            return;
        }

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(pixKey)
                .then(() => {
                    alert('Chave PIX copiada com sucesso!');
                })
                .catch(err => {
                    fallbackCopyMethod(pixKey);
                });
        } else {
            fallbackCopyMethod(pixKey);
        }
    };

    // Função para confirmar pagamento manualmente
    window.confirmarPagamento = async function() {
        const confirmBtn = document.getElementById('confirmPaymentBtn');
        const btnText = document.getElementById('confirmBtnText');
        const btnSpinner = document.getElementById('confirmBtnSpinner');

        // Desabilita o botão e mostra loading
        confirmBtn.disabled = true;
        btnText.style.display = 'none';
        btnSpinner.style.display = 'inline-block';

        try {
            const persistedData = getPersistedPaymentData();
            if (!persistedData || !persistedData.paymentId) {
                throw new Error('ID do pagamento não encontrado');
            }

            console.log('Verificação manual do pagamento:', persistedData.paymentId);

            const response = await fetch(`${baseURL}/verificar-pagamento/${persistedData.paymentId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`Erro na verificação: ${response.status}`);
            }

            const data = await response.json();
            console.log('Resultado da verificação manual:', data);

            if (data.success && data.status === 'approved') {
                alert('Pagamento confirmado com sucesso! Redirecionando...');
                isRedirecting = true;

                // Para a verificação automática
                if (checkInterval) {
                    clearInterval(checkInterval);
                }

                // Remove event listeners
                document.removeEventListener('visibilitychange', handleVisibilityChange);

                // Redireciona
                setTimeout(() => {
                    redirectToReceipt(persistedData.paymentId);
                }, 1500);

            } else if (data.status === 'pending' || data.status === 'in_process') {
                alert('Pagamento ainda está sendo processado. Aguarde alguns instantes e tente novamente.');
            } else if (data.status === 'cancelled' || data.status === 'rejected') {
                alert(`Pagamento ${data.status === 'cancelled' ? 'cancelado' : 'rejeitado'}. Você precisa gerar um novo QR Code.`);
                window.location.reload();
            } else {
                alert('Pagamento ainda não foi identificado. Verifique se o pagamento foi realizado corretamente e tente novamente em alguns instantes.');
            }

        } catch (error) {
            console.error('Erro ao confirmar pagamento:', error);
            alert('Erro ao verificar o pagamento. Por favor, tente novamente ou entre em contato com o suporte.');
        } finally {
            // Reabilita o botão
            confirmBtn.disabled = false;
            btnText.style.display = 'inline-block';
            btnSpinner.style.display = 'none';
        }
    };


    // Método alternativo para copiar texto
    function fallbackCopyMethod(text) {
        try {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.top = '0';
            textArea.style.left = '0';
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';

            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);

            if (successful) {
                alert('Chave PIX copiada com sucesso!');
            } else {
                alert('Erro ao copiar chave PIX. Por favor, tente copiar manualmente.');
            }
        } catch (err) {
            console.error('Erro ao copiar:', err);
            alert('Erro ao copiar chave PIX. Por favor, tente copiar manualmente.');
        }
    }

    // Event Listeners
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Initialize
    initializePagamento();

    // Função para voltar para a página do evento
    window.voltarParaEvento = function() {
        // Limpa dados do pagamento antes de sair
        clearCountdownTimer();
        clearPaymentRelatedLocalStorage();

        // Redireciona para a rota que leva à página de origem
        window.location.href = '/voltar-para-evento';
    };

});
