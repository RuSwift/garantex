/**
 * TRON Multisig Vue 2 Component
 * 
 * Интеграция TRON multisig с Vue 2 приложением
 * Использует TronLink для подписи транзакций
 * 
 * Подключите этот файл перед components.js:
 * <script src="/static/js/vue.min.js"></script>
 * <script src="/static/js/tron-multisig-vue.js"></script>
 * <script src="/static/js/components.js"></script>
 * 
 * Usage:
 *   <tron-multisig backend-url="/api/multisig"></tron-multisig>
 */

Vue.component('tron-multisig', {
    delimiters: ['[[', ']]'],
    props: {
        backendUrl: {
            type: String,
            default: '/api/multisig'
        },
        showFullForm: {
            type: Boolean,
            default: true
        },
        // Внешнее подключение через TronAuth
        externalAddress: {
            type: String,
            default: null
        },
        skipConnection: {
            type: Boolean,
            default: false
        },
        // Адрес multisig кошелька (сгенерирован на backend)
        multisigAddress: {
            type: String,
            default: null
        }
    },
    data() {
        return {
            // Connection
            connected: false,
            userAddress: null,
            loading: false,
            error: null,
            
            // Transaction form
            recipientAddress: '',
            amount: '',
            
            // Transaction status
            currentTx: null,
            txStatus: null,
            
            // Advanced options
            showAdvanced: false
        };
    },
    async mounted() {
        // Если передан внешний адрес (через TronAuth), использовать его
        if (this.skipConnection && this.externalAddress) {
            this.connected = true;
            this.userAddress = this.externalAddress;
            console.log('Using external wallet connection:', this.userAddress);
        } else {
            // Иначе подключаться к TronLink напрямую
            await this.initTronLink();
        }
    },
    computed: {
        formattedAddress() {
            if (!this.userAddress) return '';
            return this.userAddress.substring(0, 6) + '...' + this.userAddress.substring(this.userAddress.length - 4);
        },
        isFormValid() {
            return this.recipientAddress && 
                   this.amount && 
                   parseFloat(this.amount) > 0 &&
                   (this.multisigAddress || !this.showFullForm);
        }
    },
    methods: {
        async initTronLink() {
            this.loading = true;
            this.error = null;
            
            try {
                // Check if TronLink is installed
                if (typeof window.tronWeb === 'undefined') {
                    throw new Error('TronLink не установлен. Установите расширение TronLink.');
                }
                
                // Wait for TronLink to inject
                let attempts = 0;
                while (attempts < 50) {
                    if (window.tronWeb && window.tronWeb.ready) {
                        this.userAddress = window.tronWeb.defaultAddress.base58;
                        this.connected = true;
                        console.log('TronLink подключен:', this.userAddress);
                        this.$emit('connected', this.userAddress);
                        break;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                    attempts++;
                }
                
                if (!this.connected) {
                    throw new Error('Время ожидания подключения TronLink истекло');
                }
                
            } catch (error) {
                console.error('Ошибка инициализации TronLink:', error);
                this.error = error.message;
                this.$emit('error', error);
            } finally {
                this.loading = false;
            }
        },
        
        async createAndSignTransaction() {
            if (!this.connected) {
                this.error = 'TronLink не подключен';
                return;
            }
            
            if (!this.isFormValid) {
                this.error = 'Заполните все поля';
                return;
            }
            
            this.loading = true;
            this.error = null;
            
            try {
                // Convert TRX to SUN (1 TRX = 1,000,000 SUN)
                const amountInSun = Math.floor(parseFloat(this.amount) * 1000000);
                
                // Use multisig address from props or error
                const fromAddress = this.multisigAddress || this.userAddress;
                if (!fromAddress) {
                    throw new Error('Multisig address not set');
                }
                
                // Create transaction via TronWeb
                console.log('Создание транзакции из multisig кошелька:', fromAddress);
                const transaction = await window.tronWeb.transactionBuilder.sendTrx(
                    this.recipientAddress,
                    amountInSun,
                    fromAddress
                );
                
                console.log('Подпись транзакции через TronLink...');
                // Sign with TronLink (user will see popup)
                const signedTx = await window.tronWeb.trx.sign(transaction);
                
                console.log('Отправка подписи на сервер...');
                // Send signature to backend
                const response = await fetch(`${this.backendUrl}/add-signature`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        tx_id: transaction.txID,
                        signature: signedTx.signature[0],
                        signer_address: this.userAddress
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка добавления подписи');
                }
                
                const result = await response.json();
                
                this.currentTx = {
                    txId: transaction.txID,
                    signaturesCount: result.signatures_count,
                    requiredSignatures: result.required_signatures,
                    isReady: result.is_ready
                };
                
                console.log('Транзакция подписана:', this.currentTx);
                this.$emit('transaction-signed', this.currentTx);
                
            } catch (error) {
                console.error('Ошибка транзакции:', error);
                this.error = error.message;
                this.$emit('error', error);
            } finally {
                this.loading = false;
            }
        },
        
        async checkTransactionStatus(txId) {
            try {
                const response = await fetch(`${this.backendUrl}/transaction/${txId}`);
                if (response.ok) {
                    this.txStatus = await response.json();
                    return this.txStatus;
                }
            } catch (error) {
                console.error('Ошибка проверки статуса:', error);
            }
            return null;
        },
        
        resetForm() {
            this.recipientAddress = '';
            this.amount = '';
            this.currentTx = null;
            this.error = null;
            this.$emit('reset');
        },
        
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Visual feedback
                this.$emit('copied', text);
            }).catch(err => {
                console.error('Ошибка копирования:', err);
            });
        }
    },
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fas fa-wallet me-1"></i>
                TRON Multisig кошелек
            </div>
            <div class="card-body">
                <!-- Loading State (только если не используется внешнее подключение) -->
                <div v-if="loading && !connected && !skipConnection" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                    <p class="mt-2 text-muted">Подключение к TronLink...</p>
                </div>
                
                <!-- Error Alert -->
                <div v-else-if="error && !skipConnection" class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="fas fa-exclamation-circle"></i>
                    <strong>Ошибка:</strong> [[ error ]]
                    <button type="button" class="btn-close" @click="error = null"></button>
                </div>
                
                <!-- Connected State -->
                <div v-else-if="connected">
                    <!-- Connection Info (только если не используется внешнее подключение) -->
                    <div v-if="!skipConnection" class="alert alert-success mb-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <i class="fas fa-check-circle"></i>
                                <strong>Подключено:</strong>
                                <code class="ms-2">[[ formattedAddress ]]</code>
                            </div>
                            <button 
                                class="btn btn-sm btn-outline-success"
                                @click="copyToClipboard(userAddress)"
                                title="Копировать адрес">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Transaction Form -->
                    <div v-if="!currentTx && showFullForm">
                        <!-- Multisig Address Info (если передан) -->
                        <div v-if="multisigAddress" class="alert alert-info mb-3">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <i class="fas fa-users"></i>
                                    <strong>Multisig кошелек:</strong>
                                    <code class="ms-2">[[ multisigAddress ]]</code>
                                </div>
                                <button 
                                    type="button"
                                    class="btn btn-sm btn-outline-info"
                                    @click="copyToClipboard(multisigAddress)"
                                    title="Копировать адрес">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                            <small class="text-muted d-block mt-1">
                                Источник средств для транзакции
                            </small>
                        </div>
                        
                        <form @submit.prevent="createAndSignTransaction">
                            
                            <div class="mb-3">
                                <label class="form-label">
                                    <i class="fas fa-user"></i>
                                    Адрес получателя
                                </label>
                                <input 
                                    type="text" 
                                    class="form-control" 
                                    v-model="recipientAddress"
                                    placeholder="TRecipientAddress..."
                                    required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">
                                    <i class="fas fa-coins"></i>
                                    Сумма (TRX)
                                </label>
                                <input 
                                    type="number" 
                                    class="form-control" 
                                    v-model="amount"
                                    placeholder="1.5"
                                    step="0.000001"
                                    min="0.000001"
                                    required>
                                <small class="form-text text-muted">
                                    1 TRX = 1,000,000 SUN
                                </small>
                            </div>
                            
                            <button 
                                type="submit"
                                class="btn btn-primary w-100"
                                :disabled="loading || !isFormValid">
                                <span v-if="loading">
                                    <span class="spinner-border spinner-border-sm me-2"></span>
                                    Обработка...
                                </span>
                                <span v-else>
                                    <i class="fas fa-signature me-2"></i>
                                    Подписать транзакцию
                                </span>
                            </button>
                        </form>
                    </div>
                    
                    <!-- Transaction Status -->
                    <div v-else-if="currentTx">
                        <div class="alert" :class="currentTx.isReady ? 'alert-success' : 'alert-info'">
                            <h6 class="alert-heading">
                                <i :class="currentTx.isReady ? 'fas fa-check-circle' : 'fas fa-clock'"></i>
                                Транзакция подписана
                            </h6>
                            
                            <hr>
                            
                            <div class="mb-2">
                                <strong>ID транзакции:</strong>
                                <div class="d-flex justify-content-between align-items-center">
                                    <code class="small">[[ currentTx.txId.substring(0, 24) ]]...</code>
                                    <button 
                                        class="btn btn-sm btn-outline-secondary"
                                        @click="copyToClipboard(currentTx.txId)">
                                        <i class="fas fa-copy"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <div class="mb-2">
                                <strong>Подписей:</strong>
                                <span class="badge bg-primary ms-2">
                                    [[ currentTx.signaturesCount ]] / [[ currentTx.requiredSignatures ]]
                                </span>
                            </div>
                            
                            <div class="mt-3">
                                <p class="mb-0">
                                    <span v-if="currentTx.isReady" class="text-success">
                                        <i class="fas fa-check-circle"></i>
                                        <strong>Готово к отправке в сеть!</strong>
                                    </span>
                                    <span v-else class="text-info">
                                        <i class="fas fa-hourglass-half"></i>
                                        Ожидание еще [[ currentTx.requiredSignatures - currentTx.signaturesCount ]] подписи(ей)
                                    </span>
                                </p>
                            </div>
                        </div>
                        
                        <button class="btn btn-secondary w-100" @click="resetForm">
                            <i class="fas fa-plus me-2"></i>
                            Новая транзакция
                        </button>
                    </div>
                    
                    <!-- Compact View (no form) -->
                    <div v-if="!showFullForm" class="text-center">
                        <p class="text-muted">
                            TronLink подключен и готов к работе
                        </p>
                        <slot name="custom-controls"></slot>
                    </div>
                </div>
                
                <!-- Not Connected State (только если не используется внешнее подключение) -->
                <div v-else-if="!skipConnection" class="alert alert-warning">
                    <h6 class="alert-heading">
                        <i class="fas fa-exclamation-triangle"></i>
                        TronLink не подключен
                    </h6>
                    <p class="mb-3">
                        Убедитесь, что расширение TronLink установлено и разблокировано.
                    </p>
                    <button class="btn btn-primary" @click="initTronLink">
                        <i class="fas fa-sync-alt me-2"></i>
                        Повторить подключение
                    </button>
                </div>
            </div>
        </div>
    `
});

