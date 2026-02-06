// Modal Window Component (based on ruswift pattern)
Vue.component('modal-window', {
    delimiters: ['[[', ']]'],
    props: {
        width: {
            type: String,
            default: '50%'
        },
        height: {
            type: String,
            default: '90%'
        }
    },
    data(){
        return {
            size: {
                width: null,
                height: null
            },
            body_height: null
        }
    },
    created(){
        // Check mobile device directly
        const isMobile = window.innerWidth < 768 || window.innerHeight > window.innerWidth;
        if (isMobile) {
            this.size.width = '100%';
        }
        else {
            this.size.width = this.width;
        }
        this.size.height = this.height;
    },
    mounted(){
        const header = this.$refs.header;
        const footer = this.$refs.footer;
        const container = this.$refs.container;
        if (header && footer && container) {
            this.body_height = container.offsetHeight - header.offsetHeight - footer.offsetHeight;
            this.body_height = 9 * this.body_height / 10;
        }
    },
    computed: {
        is_mobile_device(){
            return window.innerWidth < 768 || window.innerHeight > window.innerWidth;
        },
        adaptive_modal_body_height(){
            return this.body_height;
        }
    },
    template: `
        <transition name="modal">
            <div class="modal-mask" v-if="$slots.header || $slots.body || $slots.footer">
                <div ref="wrapper" class="modal-wrapper">
                    <div ref="container" 
                         :class="{'modal-container': !is_mobile_device, 'modal-container-mobile': is_mobile_device}" 
                         :style="{'width': size.width, 'height': size.height}">
                        <div ref="header" class="modal-header">
                            <slot name="header">
                                default header
                            </slot>
                        </div>
                        
                        <div ref="body" class="modal-body" :style="{'height': adaptive_modal_body_height + 'px'}">
                            <slot name="body">
                                default body
                            </slot>
                        </div>
        
                        <div ref="footer" class="modal-footer">
                            <slot name="footer">
                                default footer
                                <button class="modal-default-button" @click="$emit('close')">
                                    OK
                                </button>
                            </slot>
                        </div>
                    </div>
                </div>
            </div>
        </transition>
    `
});

// Dashboard Component
Vue.component('Dashboard', {
    delimiters: ['[[', ']]'],
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fas fa-tachometer-alt me-1"></i>
                Dashboard
            </div>
            <div class="card-body">
                <h5>Добро пожаловать в админ-панель!</h5>
                <p>Это главная страница приложения.</p>
            </div>
        </div>
    `
});

// Profile Component
Vue.component('Profile', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            keyInfo: null,
            loading: false,
            error: null,
            // Service Endpoint editing
            editingEndpoint: false,
            serviceEndpoint: '',
            testingEndpoint: false,
            endpointVerified: false,
            endpointTestResult: null,
            savingEndpoint: false,
            endpointStatus: { message: '', type: '', visible: false }
        };
    },
    mounted() {
        this.loadKeyInfo();
    },
    methods: {
        async loadKeyInfo() {
            this.loading = true;
            this.error = null;
            try {
                const response = await fetch('/api/node/key-info');
                const contentType = response.headers.get('content-type');
                
                if (!response.ok) {
                    if (response.status === 404) {
                        this.error = 'Нода не инициализирована';
                        return;
                    }
                    
                    // Пытаемся получить JSON ошибки
                    if (contentType && contentType.includes('application/json')) {
                        try {
                            const errorData = await response.json();
                            this.error = errorData.detail || 'Ошибка загрузки информации о ключе';
                        } catch (e) {
                            this.error = `Ошибка ${response.status}: ${response.statusText}`;
                        }
                    } else {
                        // Если не JSON, показываем общую ошибку
                        this.error = `Ошибка ${response.status}: ${response.statusText}`;
                    }
                    return;
                }
                
                // Проверяем, что ответ - JSON
                if (contentType && contentType.includes('application/json')) {
                    this.keyInfo = await response.json();
                } else {
                    // Если не JSON, пытаемся распарсить как текст
                    const text = await response.text();
                    console.error('Non-JSON response:', text);
                    this.error = 'Сервер вернул неверный формат данных';
                }
            } catch (error) {
                console.error('Error loading key info:', error);
                if (error.message && error.message.includes('JSON')) {
                    this.error = 'Ошибка парсинга ответа сервера. Возможно, сервер вернул HTML вместо JSON.';
                } else {
                    this.error = error.message || 'Ошибка загрузки информации о ключе';
                }
            } finally {
                this.loading = false;
            }
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Show temporary success message
                const originalText = event.target.textContent;
                event.target.textContent = '✓ Скопировано';
                event.target.classList.add('text-success');
                setTimeout(() => {
                    event.target.textContent = originalText;
                    event.target.classList.remove('text-success');
                }, 2000);
            }).catch(err => {
                console.error('Error copying to clipboard:', err);
            });
        },
        getDefaultEndpoint() {
            // Get current page's scheme://domain and add /endpoint
            return `${window.location.origin}/endpoint`;
        },
        startEditingEndpoint() {
            this.editingEndpoint = true;
            // Use existing endpoint or default to current domain
            // Set value immediately (not just placeholder)
            this.serviceEndpoint = this.keyInfo.service_endpoint || this.getDefaultEndpoint();
            this.endpointVerified = false;
            this.endpointTestResult = null;
            this.hideEndpointStatus();
        },
        cancelEditingEndpoint() {
            this.editingEndpoint = false;
            this.serviceEndpoint = '';
            this.endpointVerified = false;
            this.endpointTestResult = null;
            this.hideEndpointStatus();
        },
        async testServiceEndpoint() {
            if (!this.serviceEndpoint || !this.serviceEndpoint.trim()) {
                this.showEndpointStatus('Введите URL эндпоинта', 'error');
                return;
            }
            
            try {
                this.testingEndpoint = true;
                this.endpointVerified = false;
                this.endpointTestResult = null;
                this.showEndpointStatus('Тестирование эндпоинта...', 'info');
                
                const response = await fetch('/api/node/test-service-endpoint', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        service_endpoint: this.serviceEndpoint
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Ошибка при тестировании эндпоинта');
                }
                
                const result = await response.json();
                this.endpointTestResult = result;
                
                if (result.success) {
                    this.endpointVerified = true;
                    this.showEndpointStatus(
                        `✅ ${result.message} (${result.response_time_ms}ms)`,
                        'success'
                    );
                } else {
                    this.endpointVerified = false;
                    this.showEndpointStatus(`❌ ${result.message}`, 'error');
                }
                
            } catch (error) {
                console.error('Error testing endpoint:', error);
                this.showEndpointStatus('Ошибка: ' + error.message, 'error');
                this.endpointVerified = false;
            } finally {
                this.testingEndpoint = false;
            }
        },
        async saveServiceEndpoint() {
            if (!this.serviceEndpoint || !this.serviceEndpoint.trim()) {
                this.showEndpointStatus('Введите URL эндпоинта', 'error');
                return;
            }
            
            if (!this.endpointVerified) {
                this.showEndpointStatus('Сначала проверьте доступность эндпоинта', 'error');
                return;
            }
            
            try {
                this.savingEndpoint = true;
                this.showEndpointStatus('Сохранение Service Endpoint...', 'info');
                
                const response = await fetch('/api/node/set-service-endpoint', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        service_endpoint: this.serviceEndpoint
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка сохранения эндпоинта');
                }
                
                this.showEndpointStatus('Service Endpoint успешно сохранен!', 'success');
                
                // Reload key info to get updated DID Document
                await this.loadKeyInfo();
                
                // Close editing mode
                setTimeout(() => {
                    this.cancelEditingEndpoint();
                }, 1500);
                
            } catch (error) {
                console.error('Error saving service endpoint:', error);
                this.showEndpointStatus('Ошибка: ' + error.message, 'error');
            } finally {
                this.savingEndpoint = false;
            }
        },
        showEndpointStatus(message, type) {
            this.endpointStatus = { message, type, visible: true };
        },
        hideEndpointStatus() {
            this.endpointStatus.visible = false;
        }
    },
    template: `
        <div class="card mb-4 profile-card-scrollable">
            <div class="card-header">
                <i class="fa-regular fa-address-card me-1"></i>
                Профиль ноды
            </div>
            <div class="card-body profile-card-body-scrollable">
                <div v-if="loading" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                    <p class="mt-2">Загрузка информации о ключе...</p>
                </div>
                
                <div v-else-if="error" class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    [[ error ]]
                </div>
                
                <div v-else-if="keyInfo" class="key-info-container">
                    <h5 class="mb-4">
                        <i class="fas fa-key me-2 text-primary"></i>
                        Публичная информация о ключе
                    </h5>
                    
                    <div class="alert alert-info mb-4">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Информация:</strong> Публичный ключ, PEM, DID и DID Document можно безопасно делиться с другими. 
                        Они используются для проверки подписей, шифрования сообщений и идентификации в P2P сети.
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">
                            <i class="fas fa-file-code me-2"></i>
                            Публичный ключ (PEM):
                        </label>
                        <div class="input-group">
                            <textarea 
                                class="form-control font-monospace" 
                                rows="6"
                                :value="keyInfo.public_key_pem" 
                                readonly
                                style="font-size: 0.8rem;"
                            ></textarea>
                            <button 
                                class="btn btn-outline-secondary" 
                                type="button"
                                @click="copyToClipboard(keyInfo.public_key_pem)"
                                title="Копировать PEM публичного ключа">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                        <small class="form-text text-muted">
                            Этот PEM ключ можно безопасно делиться - он содержит только публичную информацию
                        </small>
                    </div>
                    
                    <div class="mb-3" v-if="keyInfo.did">
                        <label class="form-label fw-bold">
                            <i class="fas fa-id-card me-2"></i>
                            DID (Decentralized Identifier):
                        </label>
                        <div class="input-group">
                            <input 
                                type="text" 
                                class="form-control font-monospace" 
                                :value="keyInfo.did" 
                                readonly
                                style="font-size: 0.9rem;"
                            />
                            <button 
                                class="btn btn-outline-secondary" 
                                type="button"
                                @click="copyToClipboard(keyInfo.did)"
                                title="Копировать DID">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                        <small class="form-text text-muted">
                            Децентрализованный идентификатор для P2P сети
                        </small>
                    </div>
                    
                    <!-- Service Endpoint Section -->
                    <hr class="my-4">
                    
                    <h5 class="mb-4">
                        <i class="fas fa-network-wired me-2 text-primary"></i>
                        Service Endpoint
                    </h5>
                    
                    <div v-if="!editingEndpoint">
                        <div class="mb-3">
                            <label class="form-label fw-bold">
                                <i class="fas fa-link me-2"></i>
                                Service Endpoint URL:
                            </label>
                            <div class="input-group">
                                <input 
                                    type="text" 
                                    class="form-control font-monospace" 
                                    :value="keyInfo.service_endpoint || 'Не настроен'" 
                                    readonly
                                    :class="{'text-muted': !keyInfo.service_endpoint}"
                                    style="font-size: 0.9rem;"
                                />
                                <button 
                                    class="btn btn-outline-primary" 
                                    type="button"
                                    @click="startEditingEndpoint"
                                    title="Редактировать Service Endpoint">
                                    <i class="fas fa-edit"></i> Редактировать
                                </button>
                            </div>
                            <small class="form-text text-muted">
                                HTTP адрес для приема DIDComm сообщений
                            </small>
                        </div>
                    </div>
                    
                    <div v-else>
                        <div v-if="endpointStatus.visible" :class="'alert alert-' + (endpointStatus.type === 'error' ? 'danger' : endpointStatus.type === 'success' ? 'success' : 'info')" style="border-radius: 10px; margin-bottom: 20px;">
                            [[ endpointStatus.message ]]
                        </div>
                        
                        <div class="mb-3">
                            <label for="edit-service-endpoint" class="form-label fw-bold">
                                <i class="fas fa-link me-2"></i>
                                Service Endpoint URL:
                            </label>
                            <input 
                                type="text"
                                id="edit-service-endpoint"
                                v-model="serviceEndpoint"
                                class="form-control"
                                placeholder="https://domain.com/endpoint"
                                @input="endpointVerified = false; endpointTestResult = null"
                            />
                            <small class="form-text text-muted" style="display: block; margin-top: 8px; font-size: 12px;">
                                URL должен быть доступен из интернета и возвращать HTTP 200 при GET запросе
                            </small>
                        </div>
                        
                        <button 
                            class="btn btn-secondary me-2 mb-2" 
                            :disabled="!serviceEndpoint || testingEndpoint"
                            @click="testServiceEndpoint">
                            [[ testingEndpoint ? '🔄 Тестирование...' : '🧪 Проверить доступность' ]]
                        </button>
                        
                        <div v-if="endpointTestResult" class="alert mb-3" :class="endpointVerified ? 'alert-success' : 'alert-danger'" style="border-radius: 10px;">
                            <strong>[[ endpointVerified ? '✅ Endpoint доступен' : '❌ Endpoint недоступен' ]]</strong>
                            <div class="mt-2">
                                <small><strong>Результат:</strong> [[ endpointTestResult.message ]]</small>
                            </div>
                            <div v-if="endpointTestResult.status_code" class="mt-1">
                                <small><strong>HTTP Status:</strong> [[ endpointTestResult.status_code ]]</small>
                            </div>
                            <div v-if="endpointTestResult.response_time_ms" class="mt-1">
                                <small><strong>Время ответа:</strong> [[ endpointTestResult.response_time_ms ]] мс</small>
                            </div>
                        </div>
                        
                        <div class="d-flex gap-2">
                            <button 
                                class="btn btn-primary" 
                                :disabled="!serviceEndpoint || !endpointVerified || savingEndpoint"
                                @click="saveServiceEndpoint">
                                [[ savingEndpoint ? 'Сохранение...' : '💾 Сохранить' ]]
                            </button>
                            
                            <button 
                                class="btn btn-secondary" 
                                :disabled="savingEndpoint"
                                @click="cancelEditingEndpoint">
                                Отмена
                            </button>
                        </div>
                    </div>
                    
                    <hr class="my-4">
                    
                    <div class="mb-3" v-if="keyInfo.did_document">
                        <label class="form-label fw-bold">
                            <i class="fas fa-file-alt me-2"></i>
                            DID Document (JSON):
                        </label>
                        <div class="input-group">
                            <textarea 
                                class="form-control font-monospace" 
                                rows="12"
                                :value="JSON.stringify(keyInfo.did_document, null, 2)" 
                                readonly
                                style="font-size: 0.75rem;"
                            ></textarea>
                            <button 
                                class="btn btn-outline-secondary" 
                                type="button"
                                @click="copyToClipboard(JSON.stringify(keyInfo.did_document, null, 2))"
                                title="Копировать DID Document">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                        <small class="form-text text-muted">
                            DID Document содержит публичные ключи и методы верификации для идентификации в P2P сети
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `
});

// Default/Empty Component (fallback)
Vue.component('Default', {
    delimiters: ['[[', ']]'],
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fas fa-info-circle me-1"></i>
                Welcome
            </div>
            <div class="card-body">
                <p>Добро пожаловать в админ-панель!</p>
            </div>
        </div>
    `
});

// Node Initialization Modal Component
Vue.component('NodeInitModal', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            show: false,
            currentStep: 1,  // 1, 2, or 3
            currentMethod: 'pem',
            mouseEntropy: [],
            entropyProgress: 0,
            requiredEntropy: 256,
            isCollecting: false,
            lastX: 0,
            lastY: 0,
            canvas: null,
            ctx: null,
            result: null,
            status: { message: '', type: '', visible: false },
            pemFile: null,
            pemPassword: '',
            pemContent: '',
            // Step 2: Root credentials
            rootCredentialMethod: 'password',
            rootUsername: '',
            rootPassword: '',
            rootPasswordConfirm: '',
            rootTronAddress: null,
            rootTronAuthenticated: false,
            savingCredentials: false,
            // Step 3: Service Endpoint
            serviceEndpoint: '',
            testingEndpoint: false,
            endpointVerified: false,
            endpointTestResult: null,
            savingEndpoint: false
        };
    },
    async mounted() {
        // Check if node needs initialization
        const initScript = document.getElementById('is-node-initialized');
        let nodeInitialized = false;
        
        if (initScript) {
            nodeInitialized = JSON.parse(initScript.textContent);
        }
        
        // Check if admin is configured
        let adminConfigured = false;
        try {
            const response = await fetch('/api/node/is-admin-configured');
            if (response.ok) {
                const data = await response.json();
                adminConfigured = data.configured;
            }
        } catch (error) {
            console.error('Error checking admin configuration:', error);
        }
        
        // Check if service endpoint is configured
        let endpointConfigured = false;
        try {
            const response = await fetch('/api/node/is-service-endpoint-configured');
            if (response.ok) {
                const data = await response.json();
                endpointConfigured = data.configured;
            }
        } catch (error) {
            console.error('Error checking service endpoint configuration:', error);
        }
        
        // Show modal if node is not fully configured
        if (!nodeInitialized || !adminConfigured || !endpointConfigured) {
            this.show = true;
            
            // Determine which step to start from
            if (!nodeInitialized) {
                // Start from Step 1: Key initialization
                this.currentStep = 1;
                this.$nextTick(() => {
                    this.initCanvas();
                });
            } else if (!adminConfigured) {
                // Skip to Step 2: Root credentials
                this.currentStep = 2;
                this.result = {
                    address: 'Already initialized',
                    keyType: 'existing',
                    message: 'Ключ ноды уже создан, настройте root доступ'
                };
            } else if (!endpointConfigured) {
                // Skip to Step 3: Service endpoint
                this.currentStep = 3;
                this.result = {
                    address: 'Already initialized',
                    keyType: 'existing'
                };
                // Set default endpoint value immediately
                this.serviceEndpoint = `${window.location.origin}/endpoint`;
                this.endpointVerified = false;
                // Try to load existing endpoint if any
                this.loadExistingEndpoint();
            }
        }
    },
    methods: {
        initCanvas() {
            this.$nextTick(() => {
                const canvas = this.$refs.entropyCanvas;
                if (canvas) {
                    this.canvas = canvas;
                    this.ctx = canvas.getContext('2d');
                    canvas.width = canvas.offsetWidth;
                    canvas.height = canvas.offsetHeight;
                }
            });
        },
        switchMethod(method) {
            this.currentMethod = method;
            this.resetForm();
            if (method === 'mouse') {
                this.$nextTick(() => {
                    this.initCanvas();
                });
            }
        },
        switchRootCredentialMethod(method) {
            this.rootCredentialMethod = method;
            this.rootUsername = '';
            this.rootPassword = '';
            this.rootPasswordConfirm = '';
            this.rootTronAddress = null;
            this.rootTronAuthenticated = false;
            this.hideStatus();
        },
        handlePemFileSelect(event) {
            const file = event.target.files[0];
            if (!file) {
                return;
            }
            
            this.pemFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.pemContent = e.target.result;
            };
            reader.onerror = () => {
                this.showStatus('Ошибка чтения файла', 'error');
            };
            reader.readAsText(file);
        },
        async generateFromPem() {
            if (!this.pemContent) {
                this.showStatus('Выберите PEM файл', 'error');
                return;
            }

            try {
                this.showStatus('Обработка PEM файла...', 'info');
                
                // Отправляем PEM на сервер
                const response = await fetch('/api/node/init-pem', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        pem_data: this.pemContent,
                        password: this.pemPassword || null
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Ошибка обработки PEM файла');
                }
                
                const data = await response.json();
                
                this.result = {
                    address: data.address,
                    keyType: data.key_type,
                    message: 'Ключ успешно загружен из PEM файла'
                };
                
                // Don't auto-reload, let user close manually after copying data
                this.showStatus('Ключ успешно сохранен! Переходите к Step 2.', 'success');
            } catch (error) {
                console.error('Error:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
            }
        },
        async proceedToStep2() {
            // Check if result exists OR if node is already initialized
            if (!this.result) {
                // Check if node might be initialized from DB
                try {
                    const response = await fetch('/api/node/key-info');
                    if (response.ok) {
                        // Node is initialized, allow to proceed
                        this.result = {
                            address: 'Already initialized',
                            keyType: 'existing',
                            message: 'Ключ ноды уже создан'
                        };
                    } else {
                        this.showStatus('Сначала завершите инициализацию ключа', 'error');
                        return;
                    }
                } catch (error) {
                    this.showStatus('Сначала завершите инициализацию ключа', 'error');
                    return;
                }
            }
            this.currentStep = 2;
            this.hideStatus();
        },
        backToStep1() {
            this.currentStep = 1;
            this.hideStatus();
        },
        handleTronAuthComplete(address, token) {
            console.log('TRON auth complete:', address, token);
            this.rootTronAddress = address;
            this.rootTronAuthenticated = true;
            this.showStatus('TRON кошелек подключен как root', 'success');
        },
        async saveRootCredentials() {
            try {
                this.savingCredentials = true;
                
                if (this.rootCredentialMethod === 'password') {
                    // Validate password credentials
                    if (!this.rootUsername || !this.rootPassword) {
                        this.showStatus('Введите логин и пароль', 'error');
                        return;
                    }
                    
                    if (this.rootPassword.length < 8) {
                        this.showStatus('Пароль должен быть минимум 8 символов', 'error');
                        return;
                    }
                    
                    if (this.rootPassword !== this.rootPasswordConfirm) {
                        this.showStatus('Пароли не совпадают', 'error');
                        return;
                    }
                    
                    this.showStatus('Сохранение root кредов...', 'info');
                    
                    // NEW API: Set password
                    const response = await fetch('/api/admin/set-password', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            username: this.rootUsername,
                            password: this.rootPassword
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Ошибка сохранения пароля');
                    }
                    
                } else if (this.rootCredentialMethod === 'tron') {
                    // Validate TRON authentication
                    if (!this.rootTronAuthenticated || !this.rootTronAddress) {
                        this.showStatus('Сначала авторизуйтесь через TRON кошелек', 'error');
                        return;
                    }
                    
                    this.showStatus('Сохранение TRON root доступа...', 'info');
                    
                    // NEW API: Add TRON address
                    const response = await fetch('/api/admin/tron-addresses', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            tron_address: this.rootTronAddress,
                            label: 'Root admin'
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Ошибка сохранения TRON адреса');
                    }
                }
                
                this.showStatus('Root креды успешно сохранены! Переход к Step 3...', 'success');
                
                // Proceed to Step 3
                setTimeout(() => {
                    this.proceedToStep3();
                }, 1500);
                
            } catch (error) {
                console.error('Error saving root credentials:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
            } finally {
                this.savingCredentials = false;
            }
        },
        proceedToStep3() {
            this.currentStep = 3;
            this.hideStatus();
            // Set default endpoint immediately (will be replaced if existing one is found)
            this.serviceEndpoint = this.getDefaultEndpoint();
            this.endpointVerified = false;
            // Try to load existing endpoint if any
            this.loadExistingEndpoint();
        },
        getDefaultEndpoint() {
            // Get current page's scheme://domain and add /endpoint
            return `${window.location.origin}/endpoint`;
        },
        backToStep2() {
            this.currentStep = 2;
            this.hideStatus();
        },
        async loadExistingEndpoint() {
            try {
                const response = await fetch('/api/node/service-endpoint');
                if (response.ok) {
                    const data = await response.json();
                    if (data.service_endpoint) {
                        // Replace default with existing endpoint
                        this.serviceEndpoint = data.service_endpoint;
                        this.endpointVerified = true;
                    }
                    // If no existing endpoint, keep the default that was already set
                }
            } catch (error) {
                console.error('Error loading existing endpoint:', error);
                // Keep the default that was already set
            }
        },
        async testServiceEndpoint() {
            if (!this.serviceEndpoint || !this.serviceEndpoint.trim()) {
                this.showStatus('Введите URL эндпоинта', 'error');
                return;
            }
            
            try {
                this.testingEndpoint = true;
                this.endpointVerified = false;
                this.endpointTestResult = null;
                this.showStatus('Тестирование эндпоинта...', 'info');
                
                const response = await fetch('/api/node/test-service-endpoint', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        service_endpoint: this.serviceEndpoint
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Ошибка при тестировании эндпоинта');
                }
                
                const result = await response.json();
                this.endpointTestResult = result;
                
                if (result.success) {
                    this.endpointVerified = true;
                    this.showStatus(
                        `✅ ${result.message} (${result.response_time_ms}ms)`,
                        'success'
                    );
                } else {
                    this.endpointVerified = false;
                    this.showStatus(`❌ ${result.message}`, 'error');
                }
                
            } catch (error) {
                console.error('Error testing endpoint:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
                this.endpointVerified = false;
            } finally {
                this.testingEndpoint = false;
            }
        },
        async saveServiceEndpoint() {
            if (!this.serviceEndpoint || !this.serviceEndpoint.trim()) {
                this.showStatus('Введите URL эндпоинта', 'error');
                return;
            }
            
            if (!this.endpointVerified) {
                this.showStatus('Сначала проверьте доступность эндпоинта', 'error');
                return;
            }
            
            try {
                this.savingEndpoint = true;
                this.showStatus('Сохранение Service Endpoint...', 'info');
                
                const response = await fetch('/api/node/set-service-endpoint', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        service_endpoint: this.serviceEndpoint
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка сохранения эндпоинта');
                }
                
                this.showStatus('Service Endpoint успешно сохранен! Инициализация завершена.', 'success');
                
                // Reload page after success
                setTimeout(() => {
                    this.closeModalComplete();
                }, 2000);
                
            } catch (error) {
                console.error('Error saving service endpoint:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
            } finally {
                this.savingEndpoint = false;
            }
        },
        resetForm() {
            this.mouseEntropy = [];
            this.entropyProgress = 0;
            this.result = null;
            this.pemFile = null;
            this.pemPassword = '';
            this.pemContent = '';
            this.hideStatus();
            if (this.canvas && this.ctx) {
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            }
        },
        handleMouseDown(e) {
            if (!this.canvas) return;
            this.isCollecting = true;
            const rect = this.canvas.getBoundingClientRect();
            this.lastX = e.clientX - rect.left;
            this.lastY = e.clientY - rect.top;
        },
        handleMouseUp() {
            this.isCollecting = false;
        },
        handleMouseMove(e) {
            if (!this.isCollecting || !this.canvas || !this.ctx) return;

            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const time = Date.now();

            const entropyData = {
                x, y,
                dx: x - this.lastX,
                dy: y - this.lastY,
                time,
                random: Math.random()
            };

            this.mouseEntropy.push(entropyData);

            // Draw trail
            this.ctx.strokeStyle = `hsl(${time % 360}, 70%, 50%)`;
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(this.lastX, this.lastY);
            this.ctx.lineTo(x, y);
            this.ctx.stroke();

            this.lastX = x;
            this.lastY = y;

            this.updateEntropyProgress();
        },
        updateEntropyProgress() {
            const estimatedBytes = this.mouseEntropy.length * 0.7;
            const previousProgress = this.entropyProgress;
            this.entropyProgress = Math.min(100, (estimatedBytes / this.requiredEntropy) * 100);
            
            // Прокрутка к кнопке, когда энтропия собрана (достигнуто 100%)
            if (previousProgress < 100 && this.entropyProgress >= 100) {
                this.$nextTick(() => {
                    this.scrollToGenerateButton();
                });
            }
        },
        async generateFromMouseEntropy() {
            if (this.mouseEntropy.length < 50) {
                this.showStatus('Недостаточно энтропии. Продолжайте двигать мышкой.', 'error');
                return;
            }

            try {
                this.showStatus('Создание ключа из энтропии...', 'info');
                
                if (typeof ethers === 'undefined') {
                    throw new Error('Ethers.js не загружен');
                }

                const seedBytes = await this.generateSeedFromMouseEntropy(16);
                const mnemonic = await this.generateMnemonicFromSeed(seedBytes);
                const wallet = ethers.Wallet.fromMnemonic(mnemonic);
                
                this.result = {
                    address: wallet.address,
                    privateKey: wallet.privateKey,
                    mnemonic: mnemonic
                };
                
                // Save to server
                await this.saveMnemonic(mnemonic);
                
                this.showStatus('Ключ успешно создан!', 'success');
                
                // Плавная прокрутка к результатам
                this.$nextTick(() => {
                    this.scrollToResult();
                });
            } catch (error) {
                console.error('Error:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
            }
        },
        async generateSeedFromMouseEntropy(byteLength = 16) {
            let entropyData = '';
            this.mouseEntropy.forEach(entropy => {
                entropyData += entropy.x + ',' + entropy.y + ',' + entropy.dx + ',' + 
                              entropy.dy + ',' + entropy.time + ',' + entropy.random + '|';
            });

            entropyData += Math.random() + ',' + Date.now() + ',' + 
                          performance.now() + ',' + Math.random() + ',' +
                          Array.from(crypto.getRandomValues(new Uint8Array(16))).join(',');

            const encoder = new TextEncoder();
            const data = encoder.encode(entropyData);
            const salt = encoder.encode('garantex-seed-salt-' + Date.now());
            
            const keyMaterial = await crypto.subtle.importKey(
                'raw', data, { name: 'PBKDF2' }, false, ['deriveBits']
            );

            const derivedBits = await crypto.subtle.deriveBits(
                {
                    name: 'PBKDF2',
                    salt: salt,
                    iterations: 100000,
                    hash: 'SHA-256'
                },
                keyMaterial,
                byteLength * 8
            );

            return new Uint8Array(derivedBits);
        },
        async generateMnemonicFromSeed(seedBytes) {
            try {
                const seedHex = Array.from(seedBytes)
                    .map(b => b.toString(16).padStart(2, '0'))
                    .join('');
                const entropy = '0x' + seedHex;
                return ethers.utils.entropyToMnemonic(entropy);
            } catch (error) {
                console.error('Error generating mnemonic:', error);
                const wallet = ethers.Wallet.createRandom();
                return wallet.mnemonic.phrase;
            }
        },
        async saveMnemonic(mnemonic) {
            try {
                const response = await fetch('/api/node/init', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ mnemonic: mnemonic })
                });
                
                if (!response.ok) {
                    throw new Error('Ошибка сохранения мнемонической фразы');
                }
                
                this.showStatus('Ключ успешно сохранен! Переходите к Step 2.', 'success');
            } catch (error) {
                console.error('Error saving mnemonic:', error);
                throw error;
            }
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.showStatus('Скопировано в буфер обмена!', 'success');
                setTimeout(() => this.hideStatus(), 2000);
            }).catch(err => {
                this.showStatus('Ошибка копирования', 'error');
            });
        },
        showStatus(message, type) {
            this.status = { message, type, visible: true };
        },
        hideStatus() {
            this.status.visible = false;
        },
        scrollToGenerateButton() {
            // Плавная прокрутка к кнопке генерации ключа
            this.$nextTick(() => {
                const generateButton = this.$refs.generateButton;
                if (generateButton) {
                    generateButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
        },
        scrollToResult() {
            // Плавная прокрутка к блоку результатов
            this.$nextTick(() => {
                const resultElement = this.$refs.resultCard;
                if (resultElement) {
                    resultElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        },
        async closeModal() {
            // Check if we can close
            // Step 3: Cannot close, must configure service endpoint
            if (this.currentStep === 3) {
                this.showStatus('Завершите настройку Service Endpoint', 'error');
                return;
            }
            
            // Step 2: Cannot close, must configure admin
            if (this.currentStep === 2) {
                this.showStatus('Завершите настройку root кредов', 'error');
                return;
            }
            
            // Step 1: Can only close if all steps are configured
            if (this.currentStep === 1) {
                // Check if result exists (node initialized in this session)
                if (!this.result) {
                    this.showStatus('Необходимо инициализировать ноду перед продолжением', 'error');
                    return;
                }
                
                // Check if admin is configured
                try {
                    const response = await fetch('/api/node/is-admin-configured');
                    if (response.ok) {
                        const data = await response.json();
                        if (!data.configured) {
                            this.showStatus('Необходимо настроить root доступ (Шаг 2)', 'error');
                            return;
                        }
                    }
                } catch (error) {
                    console.error('Error checking admin:', error);
                }
                
                // Check if service endpoint is configured
                try {
                    const response = await fetch('/api/node/is-service-endpoint-configured');
                    if (response.ok) {
                        const data = await response.json();
                        if (!data.configured) {
                            this.showStatus('Необходимо настроить Service Endpoint (Шаг 3)', 'error');
                            return;
                        }
                    }
                } catch (error) {
                    console.error('Error checking service endpoint:', error);
                }
            }
            
            // If we reach here, all steps are configured
            this.showStatus('Завершите инициализацию перед закрытием', 'error');
        },
        closeModalComplete() {
            this.show = false;
            location.reload();
        }
    },
    computed: {
        canGenerateFromMouse() {
            return this.entropyProgress >= 100;
        }
    },
    template: `
        <modal-window v-if="show" :width="'90%'" @close="closeModal">
            <template #header>
                <h3>🔑 Инициализация ноды - Шаг [[ currentStep ]] из 3</h3>
            </template>
            <template #body>
                <div v-if="status.visible" :class="'alert alert-' + (status.type === 'error' ? 'danger' : status.type === 'success' ? 'success' : 'info')" style="border-radius: 10px; margin-bottom: 20px;">
                    [[ status.message ]]
                </div>
                
                <!-- Step 1: Key Initialization -->
                <div v-if="currentStep === 1">
                <p class="seed-modal-intro">Для работы ноды в одноранговой P2P сети необходим крипто-ключ</p>
                
                <div class="method-selector">
                    <button type="button" 
                            :class="'method-btn ' + (currentMethod === 'pem' ? 'active' : '')"
                            @click="switchMethod('pem')">
                        📄 PEM файл
                    </button>
                    <button type="button" 
                            :class="'method-btn ' + (currentMethod === 'mouse' ? 'active' : '')"
                            @click="switchMethod('mouse')">
                        🖱️ Генерация ключа
                    </button>
                </div>
                
                <!-- PEM Method -->
                <div v-if="currentMethod === 'pem'" class="method-content">
                    <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                        <strong>ℹ️ Информация</strong> Загрузите PEM файл с приватным ключом (<a href="https://www.openssl.org/docs/man1.1.1/man1/ecparam.html" target="_blank" rel="noopener noreferrer">сгенерировать с помощью OpenSSL</a>).
                    </div>
                    <div class="seed-form-group">
                        <label for="pem-file-input" class="seed-form-label">Выберите PEM файл:</label>
                        <div class="seed-file-input-wrapper">
                            <input 
                                type="file"
                                id="pem-file-input"
                                ref="pemFileInput"
                                @change="handlePemFileSelect"
                                accept=".pem,.key"
                                class="form-control"
                            />
                        </div>
                        <small class="form-text text-muted" style="display: block; margin-top: 8px; font-size: 12px;">
                            Поддерживаются файлы в формате PEM (PKCS8, PKCS1, SEC1)
                        </small>
                    </div>
                    <div class="seed-form-group" v-if="pemFile">
                        <label for="pem-password" class="seed-form-label">Пароль (если PEM файл зашифрован):</label>
                        <input 
                            type="password"
                            id="pem-password"
                            v-model="pemPassword"
                            class="form-control seed-textarea"
                            placeholder="Оставьте пустым, если файл не зашифрован"
                        />
                    </div>
                    <button 
                        class="seed-btn-primary" 
                        :disabled="!pemContent"
                        @click="generateFromPem">
                        Загрузить ключ из PEM
                    </button>
                </div>
                        
                <!-- Mouse Method -->
                <div v-if="currentMethod === 'mouse'" class="method-content">
                    <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                        <strong>ℹ️ Информация</strong> Перемещайте курсор мыши по области ниже для сбора энтропии, необходимой для генерации криптографического ключа.
                    </div>
                    <div class="seed-form-group">
                        <div class="seed-progress-container">
                            <div class="seed-progress-bar">
                                <div class="seed-progress-fill" :style="{width: entropyProgress + '%'}">
                                    [[ Math.round(entropyProgress) ]]%
                                </div>
                            </div>
                        </div>
                        <div class="seed-canvas-container">
                            <canvas 
                                ref="entropyCanvas"
                                @mousedown="handleMouseDown"
                                @mouseup="handleMouseUp"
                                @mouseleave="handleMouseUp"
                                @mousemove="handleMouseMove"
                                style="height: 300px;"
                            ></canvas>
                        </div>
                    </div>
                    <button 
                        ref="generateButton"
                        class="seed-btn-primary" 
                        :disabled="!canGenerateFromMouse"
                        @click="generateFromMouseEntropy">
                        Создать ключ из энтропии
                    </button>
                </div>
                        
                <!-- Result -->
                <div v-if="result" ref="resultCard" class="seed-result-card">
                    <div class="seed-result-title">
                        <span>✅</span>
                        <span>[[ result.keyType === 'existing' ? 'Ключ уже создан' : 'Ключ успешно создан' ]]</span>
                    </div>
                    <div class="seed-result-item" v-if="result.address && result.keyType !== 'existing'">
                        <label class="seed-result-label">Адрес кошелька:</label>
                        <div class="seed-result-value">[[ result.address ]]</div>
                        <button class="seed-copy-btn" @click="copyToClipboard(result.address)">
                            📋 Копировать адрес
                        </button>
                    </div>
                    <div class="seed-result-item" v-if="result.mnemonic">
                        <label class="seed-result-label">Мнемоническая фраза:</label>
                        <div class="seed-result-value">[[ result.mnemonic ]]</div>
                        <button class="seed-copy-btn" @click="copyToClipboard(result.mnemonic)">
                            📋 Копировать фразу
                        </button>
                    </div>
                    <div class="seed-result-item" v-if="result.keyType && result.keyType !== 'existing'">
                        <label class="seed-result-label">Тип ключа:</label>
                        <div class="seed-result-value">[[ result.keyType ]]</div>
                    </div>
                    <div class="alert alert-warning mt-3" style="border-radius: 10px; border-left: 4px solid #ffc107;" v-if="result.keyType !== 'existing'">
                        <strong>🔒 Безопасность</strong> Сохраните эту информацию в безопасном месте.
                    </div>
                    <div class="alert alert-info mt-3" style="border-radius: 10px; border-left: 4px solid #0dcaf0;" v-if="result.keyType === 'existing'">
                        <strong>ℹ️ Информация</strong> Ключ ноды уже настроен. Перейдите к настройке root доступа.
                    </div>
                    
                    <button 
                        class="seed-btn-primary" 
                        style="margin-top: 20px;"
                        @click="proceedToStep2">
                        Далее: Создать Root Креды →
                    </button>
                </div>
                </div>
                
                <!-- Step 2: Root Credentials -->
                <div v-if="currentStep === 2">
                    <p class="seed-modal-intro">Создайте root учетные данные для доступа к ноде</p>
                    
                    <div class="method-selector">
                        <button type="button" 
                                :class="'method-btn ' + (rootCredentialMethod === 'password' ? 'active' : '')"
                                @click="switchRootCredentialMethod('password')">
                            🔐 Логин + Пароль
                        </button>
                        <button type="button" 
                                :class="'method-btn ' + (rootCredentialMethod === 'tron' ? 'active' : '')"
                                @click="switchRootCredentialMethod('tron')">
                            🔗 TRON Auth
                        </button>
                    </div>
                    
                    <!-- Password Method -->
                    <div v-if="rootCredentialMethod === 'password'" class="method-content">
                        <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                            <strong>ℹ️ Информация</strong> Создайте логин и пароль для root доступа к ноде.
                        </div>
                        <div class="seed-form-group">
                            <label for="root-username" class="seed-form-label">Логин:</label>
                            <input 
                                type="text"
                                id="root-username"
                                v-model="rootUsername"
                                class="form-control"
                                placeholder="Введите логин (минимум 3 символа)"
                            />
                        </div>
                        <div class="seed-form-group">
                            <label for="root-password" class="seed-form-label">Пароль:</label>
                            <input 
                                type="password"
                                id="root-password"
                                v-model="rootPassword"
                                class="form-control"
                                placeholder="Минимум 8 символов"
                            />
                        </div>
                        <div class="seed-form-group">
                            <label for="root-password-confirm" class="seed-form-label">Подтвердите пароль:</label>
                            <input 
                                type="password"
                                id="root-password-confirm"
                                v-model="rootPasswordConfirm"
                                class="form-control"
                                placeholder="Повторите пароль"
                            />
                        </div>
                        <button 
                            class="seed-btn-primary" 
                            :disabled="!rootUsername || !rootPassword || !rootPasswordConfirm || savingCredentials"
                            @click="saveRootCredentials">
                            [[ savingCredentials ? 'Сохранение...' : 'Сохранить Root Креды' ]]
                        </button>
                    </div>
                    
                    <!-- TRON Auth Method -->
                    <div v-if="rootCredentialMethod === 'tron'" class="method-content">
                        <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                            <strong>ℹ️ Информация</strong> Используйте TRON кошелек для авторизации как root. Ваш адрес будет добавлен в whitelist администраторов.
                        </div>
                        
                        <div v-if="!rootTronAuthenticated" style="padding: 20px; background: #f8f9fa; border-radius: 10px; margin-bottom: 20px;">
                            <p style="margin-bottom: 15px; color: #666;">Подключите TRON кошелек для настройки root доступа:</p>
                            <tron-auth @authenticated="handleTronAuthComplete"></tron-auth>
                        </div>
                        
                        <div v-if="rootTronAuthenticated" class="seed-result-card">
                            <div class="seed-result-title">
                                <span>✅</span>
                                <span>TRON кошелек подключен</span>
                            </div>
                            <div class="seed-result-item">
                                <label class="seed-result-label">TRON Address:</label>
                                <div class="seed-result-value">[[ rootTronAddress ]]</div>
                            </div>
                            <button 
                                class="seed-btn-primary" 
                                style="margin-top: 20px;"
                                :disabled="savingCredentials"
                                @click="saveRootCredentials">
                                [[ savingCredentials ? 'Сохранение...' : 'Сохранить TRON Root Доступ' ]]
                            </button>
                        </div>
                    </div>
                    
                    <button 
                        class="seed-btn-secondary" 
                        style="margin-top: 20px;"
                        @click="backToStep1">
                        ← Назад к Шагу 1
                    </button>
                </div>
                
                <!-- Step 3: Service Endpoint -->
                <div v-if="currentStep === 3">
                    <p class="seed-modal-intro">Настройте Service Endpoint для DIDComm сообщений</p>
                    
                    <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                        <strong>ℹ️ Информация</strong> Service Endpoint - это HTTP адрес, по которому нода будет принимать DIDComm сообщения. 
                        Формат: <code>https://your-domain.com/endpoint</code> или <code>http://your-ip:port/endpoint</code>
                    </div>
                    
                    <div class="method-content">
                        <div class="seed-form-group">
                            <label for="service-endpoint" class="seed-form-label">Service Endpoint URL:</label>
                            <input 
                                type="text"
                                id="service-endpoint"
                                v-model="serviceEndpoint"
                                class="form-control"
                                placeholder="https://domain.com/endpoint"
                                @input="endpointVerified = false; endpointTestResult = null"
                            />
                            <small class="form-text text-muted" style="display: block; margin-top: 8px; font-size: 12px;">
                                URL должен быть доступен из интернета и возвращать HTTP 200 при GET запросе
                            </small>
                        </div>
                        
                        <button 
                            class="seed-btn-secondary" 
                            :disabled="!serviceEndpoint || testingEndpoint"
                            @click="testServiceEndpoint"
                            style="margin-bottom: 15px;">
                            [[ testingEndpoint ? '🔄 Тестирование...' : '🧪 Проверить доступность' ]]
                        </button>
                        
                        <div v-if="endpointTestResult" class="seed-result-card" style="margin-bottom: 20px;">
                            <div class="seed-result-title" :style="{backgroundColor: endpointVerified ? '#d4edda' : '#f8d7da'}">
                                <span>[[ endpointVerified ? '✅' : '❌' ]]</span>
                                <span>[[ endpointVerified ? 'Endpoint доступен' : 'Endpoint недоступен' ]]</span>
                            </div>
                            <div class="seed-result-item">
                                <label class="seed-result-label">Результат проверки:</label>
                                <div class="seed-result-value">[[ endpointTestResult.message ]]</div>
                            </div>
                            <div class="seed-result-item" v-if="endpointTestResult.status_code">
                                <label class="seed-result-label">HTTP Status:</label>
                                <div class="seed-result-value">[[ endpointTestResult.status_code ]]</div>
                            </div>
                            <div class="seed-result-item" v-if="endpointTestResult.response_time_ms">
                                <label class="seed-result-label">Время ответа:</label>
                                <div class="seed-result-value">[[ endpointTestResult.response_time_ms ]] мс</div>
                            </div>
                        </div>
                        
                        <button 
                            class="seed-btn-primary" 
                            :disabled="!serviceEndpoint || !endpointVerified || savingEndpoint"
                            @click="saveServiceEndpoint">
                            [[ savingEndpoint ? 'Сохранение...' : '💾 Сохранить и завершить' ]]
                        </button>
                    </div>
                    
                    <button 
                        class="seed-btn-secondary" 
                        style="margin-top: 20px;"
                        @click="backToStep2">
                        ← Назад к Шагу 2
                    </button>
                </div>
            </template>
            <template #footer>
                <button class="modal-default-button btn btn-secondary" @click="closeModal" :disabled="(currentStep === 2 && !result) || currentStep === 3">
                    [[ currentStep === 3 ? 'Завершите настройку endpoint' : (currentStep === 2 ? 'Завершите настройку root' : (!result ? 'Инициализируйте ноду' : 'Закрыть')) ]]
                </button>
            </template>
        </modal-window>
    `
});

// Sample Component (for testing)
Vue.component('Sample', {
    props: {},
        delimiters: ['[[', ']]'],
        methods: {
            account_edited(data) {
                console.log(data)
            },
            click(){
                //this.$refs.form.validate();
            }
        },
        template: `
            <div class="w-100">
                <button @click="click">test</button>
                <auth-fields-form
                    ref="form"
                    @on_edit="account_edited"
                ></auth-fields-form>
            </div>
        `
});

// Web3 Authentication Component
Vue.component('Web3Auth', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            // API base URL
            apiBase: '',
            
            // Supported networks configuration
            supportedNetworks: {
                1: {
                    chainId: '0x1',
                    chainName: 'Ethereum Mainnet',
                    nativeCurrency: {
                        name: 'Ether',
                        symbol: 'ETH',
                        decimals: 18
                    },
                    rpcUrls: ['https://mainnet.infura.io/v3/'],
                    blockExplorerUrls: ['https://etherscan.io']
                }
            },
            
            // State
            walletAddress: null,
            isAuthenticated: false,
            currentChainId: null,
            isConnecting: false,
            isSigning: false,
            
            // UI state
            statusMessage: '',
            statusType: 'info',
            statusVisible: false,
            messageToSign: '',
            signature: '',
            
            // MetaMask availability
            isMetaMaskAvailable: false
        };
    },
    
    computed: {
        currentNetworkName() {
            if (this.currentChainId === null) return '-';
            const network = this.supportedNetworks[this.currentChainId];
            return network ? network.chainName : `Unknown Network (${this.currentChainId})`;
        },
        
        isNetworkSupported() {
            return this.currentChainId !== null && this.currentChainId in this.supportedNetworks;
        },
        
        supportedNetworksList() {
            return Object.keys(this.supportedNetworks).map(chainId => ({
                chainId: parseInt(chainId),
                network: this.supportedNetworks[chainId]
            }));
        }
    },
    
    mounted() {
        this.checkMetaMask();
        this.initNetwork();
        this.checkExistingAuth();
        this.setupEventListeners();
    },
    
    beforeDestroy() {
        this.removeEventListeners();
    },
    
    methods: {
        /**
         * Show status message
         */
        showStatus(message, type = 'info') {
            this.statusMessage = message;
            this.statusType = type;
            this.statusVisible = true;
            
            // Auto-hide success messages after 3 seconds
            if (type === 'success') {
                setTimeout(() => {
                    this.statusVisible = false;
                }, 3000);
            }
        },
        
        /**
         * Hide status message
         */
        hideStatus() {
            this.statusVisible = false;
        },
        
        /**
         * Check if Metamask is installed
         */
        checkMetaMask() {
            if (typeof window.ethereum === 'undefined') {
                this.showStatus('Metamask is not installed. Please install Metamask to continue.', 'error');
                this.isMetaMaskAvailable = false;
                return false;
            }
            this.isMetaMaskAvailable = true;
            return true;
        },
        
        /**
         * Get current chain ID from MetaMask
         */
        async getCurrentChainId() {
            try {
                const chainId = await window.ethereum.request({
                    method: 'eth_chainId'
                });
                return parseInt(chainId, 16);
            } catch (error) {
                console.error('Error getting chain ID:', error);
                return null;
            }
        },
        
        /**
         * Switch to a specific network
         */
        async switchNetwork(chainId) {
            if (!window.ethereum) {
                this.showStatus('MetaMask is not installed', 'error');
                return;
            }

            const network = this.supportedNetworks[chainId];
            if (!network) {
                this.showStatus('Network not supported', 'error');
                return;
            }

            try {
                this.showStatus(`Switching to ${network.chainName}...`, 'info');
                
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: network.chainId }]
                });
                
                // Update current chain ID
                this.currentChainId = chainId;
                this.showStatus(`Switched to ${network.chainName}`, 'success');
                
            } catch (error) {
                // If the chain hasn't been added to MetaMask, add it
                if (error.code === 4902) {
                    try {
                        await window.ethereum.request({
                            method: 'wallet_addEthereumChain',
                            params: [network]
                        });
                        this.currentChainId = chainId;
                        this.showStatus(`Added and switched to ${network.chainName}`, 'success');
                    } catch (addError) {
                        console.error('Error adding chain:', addError);
                        this.showStatus(`Error adding network: ${addError.message}`, 'error');
                    }
                } else if (error.code === 4001) {
                    this.showStatus('Network switch was rejected', 'error');
                } else {
                    console.error('Error switching network:', error);
                    this.showStatus(`Error switching network: ${error.message}`, 'error');
                }
            }
        },
        
        /**
         * Initialize network information
         */
        async initNetwork() {
            if (!window.ethereum) {
                return;
            }

            try {
                this.currentChainId = await this.getCurrentChainId();
            } catch (error) {
                console.error('Error initializing network:', error);
            }
        },
        
        /**
         * Request account access from Metamask
         */
        async requestAccountAccess() {
            try {
                const accounts = await window.ethereum.request({
                    method: 'eth_requestAccounts'
                });
                return accounts[0];
            } catch (error) {
                if (error.code === 4001) {
                    this.showStatus('Please connect to Metamask to continue.', 'error');
                } else {
                    this.showStatus(`Error connecting to Metamask: ${error.message}`, 'error');
                }
                throw error;
            }
        },
        
        /**
         * Get nonce from backend
         */
        async getNonce(address) {
            try {
                const response = await fetch(`${this.apiBase}/auth/nonce`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ wallet_address: address })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to get nonce');
                }

                const data = await response.json();
                return data;
            } catch (error) {
                this.showStatus(`Error getting nonce: ${error.message}`, 'error');
                throw error;
            }
        },
        
        /**
         * Sign message with Metamask
         */
        async signMessage(message, address) {
            try {
                const signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [message, address]
                });
                return signature;
            } catch (error) {
                if (error.code === 4001) {
                    this.showStatus('Message signature was rejected.', 'error');
                } else {
                    this.showStatus(`Error signing message: ${error.message}`, 'error');
                }
                throw error;
            }
        },
        
        /**
         * Verify signature and get JWT token
         */
        async verifySignature(address, signature, message) {
            try {
                const response = await fetch(`${this.apiBase}/auth/verify`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        wallet_address: address,
                        signature: signature,
                        message: message
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to verify signature');
                }

                const data = await response.json();
                return data.token;
            } catch (error) {
                this.showStatus(`Error verifying signature: ${error.message}`, 'error');
                throw error;
            }
        },
        
        /**
         * Store token in cookie
         */
        storeToken(token) {
            // Set cookie with token (expires in 24 hours)
            const expires = new Date();
            expires.setTime(expires.getTime() + 24 * 60 * 60 * 1000);
            document.cookie = `auth_token=${token}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
        },
        
        /**
         * Remove token from cookie
         */
        removeToken() {
            document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        },
        
        /**
         * Connect to Metamask and authenticate
         */
        async connect() {
            if (!this.checkMetaMask()) {
                return;
            }

            try {
                this.isConnecting = true;
                this.hideStatus();

                // Request account access
                const address = await this.requestAccountAccess();
                this.walletAddress = address;

                // Get current chain ID
                this.currentChainId = await this.getCurrentChainId();

                this.showStatus('Getting authentication challenge...', 'info');

                // Get nonce from backend
                const { nonce, message } = await this.getNonce(address);

                this.showStatus('Please sign the message in Metamask...', 'info');

                // Sign message with Metamask
                const signature = await this.signMessage(message, address);

                this.showStatus('Verifying signature...', 'info');

                // Verify signature and get token
                const token = await this.verifySignature(address, signature, message);

                // Store token
                this.storeToken(token);
                this.isAuthenticated = true;

                // Update UI
                this.showStatus('Successfully authenticated!', 'success');

            } catch (error) {
                console.error('Authentication error:', error);
                this.walletAddress = null;
                this.isAuthenticated = false;
            } finally {
                this.isConnecting = false;
            }
        },
        
        /**
         * Disconnect wallet
         */
        disconnect() {
            this.walletAddress = null;
            this.isAuthenticated = false;
            this.removeToken();
            this.showStatus('Disconnected successfully', 'info');
            // Clear signature result
            this.signature = '';
            this.messageToSign = '';
            // Reset network info
            this.currentChainId = null;
        },
        
        /**
         * Sign arbitrary text with Metamask
         */
        async signText() {
            if (!this.isAuthenticated) {
                this.showStatus('Please connect and authenticate first', 'error');
                return;
            }

            const text = this.messageToSign.trim();
            
            if (!text) {
                this.showStatus('Please enter some text to sign', 'error');
                return;
            }

            try {
                this.isSigning = true;
                this.hideStatus();

                // Get current account from MetaMask
                const accounts = await window.ethereum.request({
                    method: 'eth_accounts'
                });

                if (!accounts || accounts.length === 0) {
                    this.showStatus('No account connected. Please connect MetaMask.', 'error');
                    return;
                }

                const currentAddress = accounts[0];

                this.showStatus('Please sign the message in Metamask...', 'info');

                // Sign message with Metamask
                const signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [text, currentAddress]
                });

                // Display signature
                this.signature = signature;
                
                this.showStatus('Message signed successfully!', 'success');

            } catch (error) {
                console.error('Signing error:', error);
                if (error.code === 4001) {
                    this.showStatus('Message signature was rejected.', 'error');
                } else {
                    this.showStatus(`Error signing message: ${error.message}`, 'error');
                }
                this.signature = '';
            } finally {
                this.isSigning = false;
            }
        },
        
        /**
         * Handle keydown event for message input
         */
        handleKeyDown(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.signText();
            }
        },
        
        /**
         * Handle account changes in Metamask
         */
        handleAccountsChanged(accounts) {
            if (accounts.length === 0) {
                // User disconnected from Metamask
                this.disconnect();
            } else if (accounts[0].toLowerCase() !== (this.walletAddress || '').toLowerCase()) {
                // User switched accounts
                this.walletAddress = accounts[0];
                if (this.isAuthenticated) {
                    // Re-authenticate with new account
                    this.connect();
                }
            }
        },
        
        /**
         * Handle chain changes in Metamask
         */
        async handleChainChanged(chainIdHex) {
            // Update chain ID when user switches networks
            this.currentChainId = parseInt(chainIdHex, 16);
            
            // Show notification about network change
            const networkName = this.currentNetworkName;
            if (this.isNetworkSupported) {
                this.showStatus(`Network changed to ${networkName}`, 'info');
            } else {
                this.showStatus(`Unsupported network: ${networkName}. Please switch to a supported network.`, 'error');
            }
        },
        
        /**
         * Setup Metamask event listeners
         */
        setupEventListeners() {
            if (window.ethereum) {
                window.ethereum.on('accountsChanged', this.handleAccountsChanged);
                window.ethereum.on('chainChanged', this.handleChainChanged);
            }
        },
        
        /**
         * Remove Metamask event listeners
         */
        removeEventListeners() {
            if (window.ethereum) {
                window.ethereum.removeListener('accountsChanged', this.handleAccountsChanged);
                window.ethereum.removeListener('chainChanged', this.handleChainChanged);
            }
        },
        
        /**
         * Check if user is already authenticated
         */
        async checkExistingAuth() {
            // Check if we have a token in cookies
            const cookies = document.cookie.split(';');
            const tokenCookie = cookies.find(c => c.trim().startsWith('auth_token='));
            
            if (tokenCookie) {
                const token = tokenCookie.split('=')[1];
                // Try to verify token with backend
                try {
                    const response = await fetch(`${this.apiBase}/auth/me`, {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (response.ok) {
                        const userInfo = await response.json();
                        this.walletAddress = userInfo.wallet_address;
                        this.isAuthenticated = true;
                        return;
                    }
                } catch (error) {
                    console.error('Error checking auth:', error);
                }
            }

            // If no valid token, check if Metamask is already connected
            if (window.ethereum) {
                try {
                    const accounts = await window.ethereum.request({
                        method: 'eth_accounts'
                    });
                    if (accounts.length > 0) {
                        this.walletAddress = accounts[0];
                        // Don't auto-authenticate, just show connect button
                    }
                } catch (error) {
                    console.error('Error checking accounts:', error);
                }
            }
        }
    },
    
    template: `
        <div class="web3-auth-container">
            <div class="container">
                <h1>🔐 Web3 Authentication</h1>
                <p class="subtitle">Connect with Metamask to authenticate</p>

                <div v-if="statusVisible" :class="['status', statusType]">
                    [[ statusMessage ]]
                </div>

                <div v-if="!isAuthenticated" id="not-connected">
                    <button 
                        id="connect-btn" 
                        @click="connect"
                        :disabled="isConnecting || !isMetaMaskAvailable"
                    >
                        <span v-if="isConnecting" class="loading"></span>
                        [[ isConnecting ? 'Connecting...' : 'Connect Metamask' ]]
                    </button>
                    <p style="color: #999; font-size: 12px; margin-top: 20px;">
                        Make sure you have Metamask installed and unlocked
                    </p>
                </div>

                <div v-else id="connected">
                    <button id="disconnect-btn" class="secondary" @click="disconnect">
                        Disconnect
                    </button>
                    
                    <div class="user-info">
                        <h3>Authenticated</h3>
                        <p><strong>Wallet Address:</strong> [[ walletAddress ]]</p>
                        <p><strong>Status:</strong> <span id="auth-status">Authenticated</span></p>
                    </div>

                    <div class="network-section">
                        <h3>🌐 Network</h3>
                        <div class="network-info">
                            <span class="network-name">Current: [[ currentNetworkName ]]</span>
                            <span 
                                :class="['network-badge', { 'unsupported': !isNetworkSupported }]"
                            >
                                Chain ID: [[ currentChainId || '-' ]]
                            </span>
                        </div>
                        <div class="network-selector">
                            <button
                                v-for="item in supportedNetworksList"
                                :key="item.chainId"
                                :class="['network-btn', { 'active': item.chainId === currentChainId }]"
                                @click="switchNetwork(item.chainId)"
                            >
                                <span class="network-name">[[ item.network.chainName ]]</span>
                                <span class="network-chain-id">Chain ID: [[ item.chainId ]]</span>
                            </button>
                        </div>
                    </div>

                    <div class="sign-section">
                        <h3>✍️ Sign Message</h3>
                        <label for="message-input">Enter text to sign:</label>
                        <textarea
                            id="message-input"
                            v-model="messageToSign"
                            placeholder="Type any message you want to sign with your wallet..."
                            @keydown="handleKeyDown"
                        ></textarea>
                        <button 
                            id="sign-btn"
                            @click="signText"
                            :disabled="isSigning || !messageToSign.trim()"
                        >
                            <span v-if="isSigning" class="loading"></span>
                            [[ isSigning ? 'Signing...' : 'Sign with MetaMask' ]]
                        </button>
                        <div v-if="signature" class="signature-result">
                            <strong>Signature:</strong>
                            <div>[[ signature ]]</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});

// Web3 Authentication Component for Mobile Devices
Vue.component('Web3AuthMobile', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            // API base URL
            apiBase: '',
            
            // Supported networks configuration
            supportedNetworks: {
                1: {
                    chainId: '0x1',
                    chainName: 'Ethereum Mainnet',
                    nativeCurrency: {
                        name: 'Ether',
                        symbol: 'ETH',
                        decimals: 18
                    },
                    rpcUrls: ['https://mainnet.infura.io/v3/'],
                    blockExplorerUrls: ['https://etherscan.io']
                }
            },
            
            // State
            walletAddress: null,
            isAuthenticated: false,
            currentChainId: null,
            isConnecting: false,
            isSigning: false,
            
            // UI state
            statusMessage: '',
            statusType: 'info',
            statusVisible: false,
            messageToSign: '',
            signature: '',
            showNetworkSelector: false,
            showSignSection: false,
            
            // MetaMask availability
            isMetaMaskAvailable: false,
            
            // Mobile device detection
            isMobileDevice: false,
            useDeepLink: false,
            waitingForCallback: false
        };
    },
    
    computed: {
        currentNetworkName() {
            if (this.currentChainId === null) return '-';
            const network = this.supportedNetworks[this.currentChainId];
            return network ? network.chainName : `Network ${this.currentChainId}`;
        },
        
        isNetworkSupported() {
            return this.currentChainId !== null && this.currentChainId in this.supportedNetworks;
        },
        
        supportedNetworksList() {
            return Object.keys(this.supportedNetworks).map(chainId => ({
                chainId: parseInt(chainId),
                network: this.supportedNetworks[chainId]
            }));
        },
        
        shortAddress() {
            if (!this.walletAddress) return '';
            return `${this.walletAddress.slice(0, 6)}...${this.walletAddress.slice(-4)}`;
        }
    },
    
    mounted() {
        // Сначала определяем мобильное устройство
        this.detectMobileDevice();
        
        // Если это мобильное устройство без window.ethereum, настраиваем для deep linking
        if (this.isMobileDevice && !window.ethereum) {
            this.useDeepLink = true;
            this.isMetaMaskAvailable = true;
            // Очищаем статус, чтобы не показывать ошибку
            this.statusVisible = false;
            this.statusMessage = '';
            this.statusType = 'info';
        }
        
        this.checkMetaMask();
        this.initNetwork();
        this.checkExistingAuth();
        this.setupEventListeners();
        this.checkUrlCallback();
    },
    
    beforeDestroy() {
        this.removeEventListeners();
    },
    
    methods: {
        showStatus(message, type = 'info') {
            // На мобильных устройствах не показываем ошибки о отсутствии MetaMask
            if (type === 'error' && this.isMobileDevice && !window.ethereum && 
                (message.includes('MetaMask не установлен') || message.includes('MetaMask is not installed'))) {
                // Вместо ошибки просто не показываем статус - инструкция будет в useDeepLink блоке
                return;
            }
            
            this.statusMessage = message;
            this.statusType = type;
            this.statusVisible = true;
            
            if (type === 'success') {
                setTimeout(() => {
                    this.statusVisible = false;
                }, 3000);
            }
        },
        
        hideStatus() {
            this.statusVisible = false;
        },
        
        /**
         * Определить мобильное устройство
         */
        detectMobileDevice() {
            const userAgent = navigator.userAgent || navigator.vendor || window.opera;
            const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent.toLowerCase());
            
            // Также проверяем размер экрана как дополнительный индикатор
            const isSmallScreen = window.innerWidth < 768 || (window.innerHeight > window.innerWidth && window.innerWidth < 1024);
            
            this.isMobileDevice = isMobile || isSmallScreen;
            
            // На мобильных устройствах без window.ethereum используем deep linking
            if (this.isMobileDevice) {
                this.useDeepLink = true;
                this.isMetaMaskAvailable = true; // Разрешаем подключение
            }
        },
        
        /**
         * Проверка MetaMask с поддержкой мобильных устройств
         */
        checkMetaMask() {
            // Сначала определяем мобильное устройство, если еще не определено
            if (!this.isMobileDevice) {
                this.detectMobileDevice();
            }
            
            // Если это мобильное устройство и нет window.ethereum, разрешаем deep linking
            if (this.isMobileDevice && !window.ethereum) {
                this.isMetaMaskAvailable = true; // Разрешаем подключение через deep link
                this.useDeepLink = true; // Убеждаемся, что useDeepLink установлен
                // Очищаем любые предыдущие ошибки на мобильных устройствах
                this.hideStatus();
                // НЕ показываем ошибку на мобильных устройствах - показываем инструкцию
                return true;
            }
            
            // Только для десктопа показываем ошибку, если нет window.ethereum
            if (typeof window.ethereum === 'undefined') {
                // Проверяем еще раз, не мобильное ли это устройство
                if (this.isMobileDevice) {
                    this.isMetaMaskAvailable = true;
                    this.useDeepLink = true;
                    this.hideStatus();
                    return true;
                }
                // Только для десктопа показываем ошибку
                if (!this.isMobileDevice) {
                    this.showStatus('MetaMask не установлен. Установите MetaMask для продолжения.', 'error');
                    this.isMetaMaskAvailable = false;
                    return false;
                }
            }
            this.isMetaMaskAvailable = true;
            return true;
        },
        
        async getCurrentChainId() {
            try {
                const chainId = await window.ethereum.request({
                    method: 'eth_chainId'
                });
                return parseInt(chainId, 16);
            } catch (error) {
                console.error('Error getting chain ID:', error);
                return null;
            }
        },
        
        async switchNetwork(chainId) {
            if (!window.ethereum) {
                // На мобильных устройствах не показываем ошибку
                if (!this.isMobileDevice) {
                    this.showStatus('MetaMask не установлен', 'error');
                }
                return;
            }

            const network = this.supportedNetworks[chainId];
            if (!network) {
                this.showStatus('Сеть не поддерживается', 'error');
                return;
            }

            try {
                this.showStatus(`Переключение на ${network.chainName}...`, 'info');
                
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: network.chainId }]
                });
                
                this.currentChainId = chainId;
                this.showNetworkSelector = false;
                this.showStatus(`Переключено на ${network.chainName}`, 'success');
                
            } catch (error) {
                if (error.code === 4902) {
                    try {
                        await window.ethereum.request({
                            method: 'wallet_addEthereumChain',
                            params: [network]
                        });
                        this.currentChainId = chainId;
                        this.showNetworkSelector = false;
                        this.showStatus(`Добавлена и переключена ${network.chainName}`, 'success');
                    } catch (addError) {
                        console.error('Error adding chain:', addError);
                        this.showStatus(`Ошибка добавления сети: ${addError.message}`, 'error');
                    }
                } else if (error.code === 4001) {
                    this.showStatus('Переключение сети отклонено', 'error');
                } else {
                    console.error('Error switching network:', error);
                    this.showStatus(`Ошибка переключения сети: ${error.message}`, 'error');
                }
            }
        },
        
        async initNetwork() {
            if (!window.ethereum) {
                return;
            }

            try {
                this.currentChainId = await this.getCurrentChainId();
            } catch (error) {
                console.error('Error initializing network:', error);
            }
        },
        
        /**
         * Получить deep link для MetaMask
         */
        getMetaMaskDeepLink() {
            // Формируем callback URL с параметрами
            const callbackUrl = new URL(window.location.href);
            callbackUrl.searchParams.set('action', 'connect');
            const callbackUrlString = encodeURIComponent(callbackUrl.toString());
            
            // Используем универсальную ссылку MetaMask
            return `https://metamask.app.link/dapp?url=${callbackUrlString}`;
        },
        
        /**
         * Подключение через deep link для мобильных устройств
         */
        async connectViaDeepLink() {
            const metamaskUniversalLink = this.getMetaMaskDeepLink();
            
            // Пытаемся открыть MetaMask через универсальную ссылку
            // Это работает как на iOS, так и на Android
            window.location.href = metamaskUniversalLink;
            
            this.waitingForCallback = true;
            this.showStatus('Откройте MetaMask в приложении и подтвердите подключение', 'info');
            
            // Сохраняем состояние для обработки callback
            const callbackUrl = new URL(window.location.href);
            callbackUrl.searchParams.set('action', 'connect');
            sessionStorage.setItem('metamask_connecting', 'true');
            sessionStorage.setItem('metamask_callback_url', callbackUrl.toString());
        },
        
        /**
         * Проверка URL параметров после возврата из MetaMask
         */
        checkUrlCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const address = urlParams.get('address');
            const signature = urlParams.get('signature');
            const message = urlParams.get('message');
            const action = urlParams.get('action'); // 'connect' или 'sign'
            
            if (address && signature && message) {
                if (action === 'sign') {
                    // Обработка подписи сообщения
                    this.handleSignCallback(signature);
                } else {
                    // Обработка подключения
                    this.handleMetaMaskCallback(address, signature, message);
                }
                
                // Очищаем URL параметры
                const cleanUrl = window.location.pathname;
                window.history.replaceState({}, document.title, cleanUrl);
            }
        },
        
        /**
         * Обработка callback для подписи сообщения
         */
        handleSignCallback(signature) {
            this.signature = signature;
            this.isSigning = false;
            this.showStatus('Сообщение подписано!', 'success');
        },
        
        /**
         * Обработка callback от MetaMask Mobile
         */
        async handleMetaMaskCallback(address, signature, message) {
            try {
                this.waitingForCallback = false;
                this.walletAddress = address;
                
                this.showStatus('Проверка подписи...', 'info');
                
                // Проверяем подпись и получаем токен
                const token = await this.verifySignature(address, signature, message);
                
                // Сохраняем токен
                this.storeToken(token);
                this.isAuthenticated = true;
                
                // Получаем chain ID (если доступен)
                if (window.ethereum) {
                    this.currentChainId = await this.getCurrentChainId();
                }
                
                this.showStatus('Успешно авторизован!', 'success');
                
            } catch (error) {
                console.error('Callback error:', error);
                this.showStatus(`Ошибка авторизации: ${error.message}`, 'error');
                this.walletAddress = null;
                this.isAuthenticated = false;
            } finally {
                this.isConnecting = false;
                sessionStorage.removeItem('metamask_connecting');
            }
        },
        
        async requestAccountAccess() {
            // На мобильных устройствах без window.ethereum используем deep linking
            if (this.isMobileDevice && !window.ethereum) {
                await this.connectViaDeepLink();
                // Бросаем специальную ошибку, чтобы прервать стандартный flow
                throw new Error('MOBILE_DEEP_LINK');
            }
            
            try {
                const accounts = await window.ethereum.request({
                    method: 'eth_requestAccounts'
                });
                return accounts[0];
            } catch (error) {
                if (error.code === 4001) {
                    this.showStatus('Подключитесь к MetaMask для продолжения.', 'error');
                } else {
                    this.showStatus(`Ошибка подключения к MetaMask: ${error.message}`, 'error');
                }
                throw error;
            }
        },
        
        async getNonce(address) {
            try {
                const response = await fetch(`${this.apiBase}/auth/nonce`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ wallet_address: address })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to get nonce');
                }

                const data = await response.json();
                return data;
            } catch (error) {
                this.showStatus(`Ошибка получения nonce: ${error.message}`, 'error');
                throw error;
            }
        },
        
        async signMessage(message, address) {
            // На мобильных устройствах без window.ethereum подпись происходит в приложении
            if (this.isMobileDevice && !window.ethereum) {
                // Формируем URL для подписи в MetaMask Mobile
                const signUrl = encodeURIComponent(window.location.href);
                const messageEncoded = encodeURIComponent(message);
                const addressEncoded = encodeURIComponent(address);
                
                const metamaskSignLink = `https://metamask.app.link/sign?url=${signUrl}&message=${messageEncoded}&address=${addressEncoded}`;
                window.location.href = metamaskSignLink;
                
                // Ждем callback через URL параметры
                this.waitingForCallback = true;
                throw new Error('MOBILE_SIGN_PENDING');
            }
            
            try {
                const signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [message, address]
                });
                return signature;
            } catch (error) {
                if (error.code === 4001) {
                    this.showStatus('Подпись сообщения отклонена.', 'error');
                } else {
                    this.showStatus(`Ошибка подписи: ${error.message}`, 'error');
                }
                throw error;
            }
        },
        
        async verifySignature(address, signature, message) {
            try {
                const response = await fetch(`${this.apiBase}/auth/verify`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        wallet_address: address,
                        signature: signature,
                        message: message
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to verify signature');
                }

                const data = await response.json();
                return data.token;
            } catch (error) {
                this.showStatus(`Ошибка проверки подписи: ${error.message}`, 'error');
                throw error;
            }
        },
        
        storeToken(token) {
            const expires = new Date();
            expires.setTime(expires.getTime() + 24 * 60 * 60 * 1000);
            document.cookie = `auth_token=${token}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
        },
        
        removeToken() {
            document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        },
        
        async connect() {
            if (!this.checkMetaMask()) {
                return;
            }

            try {
                this.isConnecting = true;
                this.hideStatus();

                // На мобильных устройствах без window.ethereum используем deep linking
                if (this.isMobileDevice && !window.ethereum) {
                    await this.connectViaDeepLink();
                    // После deep link ждем callback через checkUrlCallback
                    return;
                }

                const address = await this.requestAccountAccess();
                this.walletAddress = address;

                this.currentChainId = await this.getCurrentChainId();

                this.showStatus('Получение запроса на авторизацию...', 'info');

                const { nonce, message } = await this.getNonce(address);

                this.showStatus('Подпишите сообщение в MetaMask...', 'info');

                const signature = await this.signMessage(message, address);

                this.showStatus('Проверка подписи...', 'info');

                const token = await this.verifySignature(address, signature, message);

                this.storeToken(token);
                this.isAuthenticated = true;

                this.showStatus('Успешно авторизован!', 'success');

            } catch (error) {
                // Игнорируем ошибку MOBILE_DEEP_LINK, так как это ожидаемое поведение
                if (error.message !== 'MOBILE_DEEP_LINK') {
                    console.error('Authentication error:', error);
                    this.walletAddress = null;
                    this.isAuthenticated = false;
                    this.isConnecting = false;
                }
            } finally {
                // Не сбрасываем isConnecting для мобильных устройств, так как ждем callback
                if (!this.waitingForCallback) {
                    this.isConnecting = false;
                }
            }
        },
        
        disconnect() {
            this.walletAddress = null;
            this.isAuthenticated = false;
            this.removeToken();
            this.showStatus('Отключено', 'info');
            this.signature = '';
            this.messageToSign = '';
            this.currentChainId = null;
            this.showNetworkSelector = false;
            this.showSignSection = false;
            this.waitingForCallback = false;
            this.isConnecting = false;
            sessionStorage.removeItem('metamask_connecting');
        },
        
        async signText() {
            if (!this.isAuthenticated) {
                this.showStatus('Сначала подключитесь и авторизуйтесь', 'error');
                return;
            }

            const text = this.messageToSign.trim();
            
            if (!text) {
                this.showStatus('Введите текст для подписи', 'error');
                return;
            }

            try {
                this.isSigning = true;
                this.hideStatus();

                // На мобильных устройствах без window.ethereum используем deep linking
                if (this.isMobileDevice && !window.ethereum) {
                    if (!this.walletAddress) {
                        this.showStatus('Сначала подключите кошелек', 'error');
                        this.isSigning = false;
                        return;
                    }
                    
                    // Формируем callback URL с параметрами для подписи
                    const callbackUrl = new URL(window.location.href);
                    callbackUrl.searchParams.set('action', 'sign');
                    const callbackUrlString = encodeURIComponent(callbackUrl.toString());
                    
                    // Формируем URL для подписи в MetaMask Mobile
                    const messageEncoded = encodeURIComponent(text);
                    const addressEncoded = encodeURIComponent(this.walletAddress);
                    
                    const metamaskSignLink = `https://metamask.app.link/sign?url=${callbackUrlString}&message=${messageEncoded}&address=${addressEncoded}`;
                    window.location.href = metamaskSignLink;
                    
                    this.showStatus('Откройте MetaMask для подписи сообщения', 'info');
                    // Ждем callback через URL параметры
                    return;
                }

                const accounts = await window.ethereum.request({
                    method: 'eth_accounts'
                });

                if (!accounts || accounts.length === 0) {
                    this.showStatus('Аккаунт не подключен. Подключите MetaMask.', 'error');
                    return;
                }

                const currentAddress = accounts[0];

                this.showStatus('Подпишите сообщение в MetaMask...', 'info');

                const signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [text, currentAddress]
                });

                this.signature = signature;
                this.showStatus('Сообщение подписано!', 'success');

            } catch (error) {
                console.error('Signing error:', error);
                if (error.code === 4001) {
                    this.showStatus('Подпись отклонена.', 'error');
                } else {
                    this.showStatus(`Ошибка подписи: ${error.message}`, 'error');
                }
                this.signature = '';
            } finally {
                this.isSigning = false;
            }
        },
        
        handleKeyDown(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.signText();
            }
        },
        
        handleAccountsChanged(accounts) {
            if (accounts.length === 0) {
                this.disconnect();
            } else if (accounts[0].toLowerCase() !== (this.walletAddress || '').toLowerCase()) {
                this.walletAddress = accounts[0];
                if (this.isAuthenticated) {
                    this.connect();
                }
            }
        },
        
        async handleChainChanged(chainIdHex) {
            this.currentChainId = parseInt(chainIdHex, 16);
            const networkName = this.currentNetworkName;
            if (this.isNetworkSupported) {
                this.showStatus(`Сеть изменена на ${networkName}`, 'info');
            } else {
                this.showStatus(`Неподдерживаемая сеть: ${networkName}`, 'error');
            }
        },
        
        setupEventListeners() {
            if (window.ethereum) {
                window.ethereum.on('accountsChanged', this.handleAccountsChanged);
                window.ethereum.on('chainChanged', this.handleChainChanged);
            }
        },
        
        removeEventListeners() {
            if (window.ethereum) {
                window.ethereum.removeListener('accountsChanged', this.handleAccountsChanged);
                window.ethereum.removeListener('chainChanged', this.handleChainChanged);
            }
        },
        
        async checkExistingAuth() {
            const cookies = document.cookie.split(';');
            const tokenCookie = cookies.find(c => c.trim().startsWith('auth_token='));
            
            if (tokenCookie) {
                const token = tokenCookie.split('=')[1];
                try {
                    const response = await fetch(`${this.apiBase}/auth/me`, {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (response.ok) {
                        const userInfo = await response.json();
                        this.walletAddress = userInfo.wallet_address;
                        this.isAuthenticated = true;
                        return;
                    }
                } catch (error) {
                    console.error('Error checking auth:', error);
                }
            }

            if (window.ethereum) {
                try {
                    const accounts = await window.ethereum.request({
                        method: 'eth_accounts'
                    });
                    if (accounts.length > 0) {
                        this.walletAddress = accounts[0];
                    }
                } catch (error) {
                    console.error('Error checking accounts:', error);
                }
            }
        },
        
        toggleNetworkSelector() {
            this.showNetworkSelector = !this.showNetworkSelector;
        },
        
        toggleSignSection() {
            this.showSignSection = !this.showSignSection;
        }
    },
    
    template: `
        <div class="web3-auth-mobile">
            <div class="mobile-container">
                <div class="mobile-header">
                    <h1>🔐 Web3</h1>
                    <p class="mobile-subtitle">Авторизация через MetaMask</p>
                </div>

                <div v-if="statusVisible && !(useDeepLink && statusType === 'error' && statusMessage.includes('MetaMask не установлен'))" :class="['mobile-status', statusType]">
                    [[ statusMessage ]]
                </div>

                <div v-if="!isAuthenticated" class="mobile-not-connected">
                    <button 
                        class="mobile-btn mobile-btn-primary"
                        @click="connect"
                        :disabled="isConnecting || (!isMetaMaskAvailable && !useDeepLink)"
                    >
                        <span v-if="isConnecting" class="mobile-loading"></span>
                        [[ isConnecting ? 'Подключение...' : 'Подключить MetaMask' ]]
                    </button>
                    <p class="mobile-hint" v-if="!useDeepLink && isMetaMaskAvailable">
                        Убедитесь, что MetaMask установлен и разблокирован
                    </p>
                    <div v-if="useDeepLink" class="mobile-instruction">
                        <p class="mobile-hint" style="margin-bottom: 12px;">
                            <strong>📱 Мобильное устройство</strong>
                        </p>
                        <p class="mobile-hint" style="font-size: 12px; line-height: 1.5; margin-bottom: 12px;">
                            Нажмите кнопку ниже, чтобы открыть приложение MetaMask.<br>
                            Подтвердите подключение в приложении, затем вернитесь сюда.
                        </p>
                        <a 
                            :href="getMetaMaskDeepLink()"
                            class="mobile-btn mobile-btn-secondary"
                            style="text-decoration: none; display: block; margin-top: 12px;"
                        >
                            🔗 Открыть MetaMask App
                        </a>
                        <p class="mobile-hint" style="font-size: 11px; margin-top: 8px; color: #999;">
                            Если приложение не установлено, вы будете перенаправлены в App Store / Google Play
                        </p>
                    </div>
                    <div v-if="waitingForCallback" class="mobile-waiting">
                        <p class="mobile-hint" style="color: #667eea; font-weight: 600;">
                            ⏳ Ожидание подтверждения в MetaMask...
                        </p>
                    </div>
                </div>

                <div v-else class="mobile-connected">
                    <div class="mobile-user-card">
                        <div class="mobile-user-header">
                            <div class="mobile-user-icon">✓</div>
                            <div class="mobile-user-info">
                                <div class="mobile-user-label">Подключено</div>
                                <div class="mobile-user-address">[[ shortAddress ]]</div>
                            </div>
                        </div>
                        <button class="mobile-btn mobile-btn-secondary" @click="disconnect">
                            Отключить
                        </button>
                    </div>

                    <div class="mobile-section">
                        <button 
                            class="mobile-section-header"
                            @click="toggleNetworkSelector"
                        >
                            <span>🌐 Сеть: [[ currentNetworkName ]]</span>
                            <span :class="['mobile-arrow', { 'open': showNetworkSelector }]">▼</span>
                        </button>
                        <div v-if="showNetworkSelector" class="mobile-section-content">
                            <div 
                                v-for="item in supportedNetworksList"
                                :key="item.chainId"
                                :class="['mobile-network-item', { 'active': item.chainId === currentChainId }]"
                                @click="switchNetwork(item.chainId)"
                            >
                                <div class="mobile-network-name">[[ item.network.chainName ]]</div>
                                <div class="mobile-network-id">Chain ID: [[ item.chainId ]]</div>
                            </div>
                        </div>
                    </div>

                    <div class="mobile-section">
                        <button 
                            class="mobile-section-header"
                            @click="toggleSignSection"
                        >
                            <span>✍️ Подписать сообщение</span>
                            <span :class="['mobile-arrow', { 'open': showSignSection }]">▼</span>
                        </button>
                        <div v-if="showSignSection" class="mobile-section-content">
                            <textarea
                                v-model="messageToSign"
                                class="mobile-textarea"
                                placeholder="Введите текст для подписи..."
                                @keydown="handleKeyDown"
                            ></textarea>
                            <button 
                                class="mobile-btn mobile-btn-primary"
                                @click="signText"
                                :disabled="isSigning || !messageToSign.trim()"
                            >
                                <span v-if="isSigning" class="mobile-loading"></span>
                                [[ isSigning ? 'Подписание...' : 'Подписать' ]]
                            </button>
                            <div v-if="signature" class="mobile-signature">
                                <div class="mobile-signature-label">Подпись:</div>
                                <div class="mobile-signature-value">[[ signature ]]</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});

// TRON Authentication Component (Desktop + Mobile)
Vue.component('TronAuth', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            // API base URL
            apiBase: '',
            
            // State
            walletAddress: null,
            isAuthenticated: false,
            isConnecting: false,
            isSigning: false,
            
            // UI state
            statusMessage: '',
            statusType: 'info',
            statusVisible: false,
            messageToSign: '',
            signature: '',
            
            // Device detection
            isMobileDevice: false,
            
            // WalletConnect
            useWalletConnect: false,
            walletConnectProvider: null,
            waitingForCallback: false,
            
            // TRON Web availability
            isTronWebAvailable: false
        };
    },
    
    computed: {
        shortAddress() {
            if (!this.walletAddress) return '';
            return `${this.walletAddress.slice(0, 6)}...${this.walletAddress.slice(-4)}`;
        }
    },
    
    mounted() {
        this.detectMobileDevice();
        this.checkTronWebWithRetry();
        this.checkExistingAuth();
    },
    
    methods: {
        /**
         * Show status message
         */
        showStatus(message, type = 'info') {
            this.statusMessage = message;
            this.statusType = type;
            this.statusVisible = true;
            
            // Auto-hide success messages after 3 seconds
            if (type === 'success') {
                setTimeout(() => {
                    this.statusVisible = false;
                }, 3000);
            }
        },
        
        /**
         * Hide status message
         */
        hideStatus() {
            this.statusVisible = false;
        },
        
        /**
         * Detect mobile device
         */
        detectMobileDevice() {
            const userAgent = navigator.userAgent || navigator.vendor || window.opera;
            const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent.toLowerCase());
            const isSmallScreen = window.innerWidth < 768 || (window.innerHeight > window.innerWidth && window.innerWidth < 1024);
            
            this.isMobileDevice = isMobile || isSmallScreen;
        },
        
        /**
         * Check TronWeb with retry logic (для асинхронной инжекции от TrustWallet)
         */
        checkTronWebWithRetry() {
            console.log('=== TronAuth: Starting TronWeb detection with retry ===');
            
            let attempts = 0;
            const maxAttempts = 20; // 20 попыток = 6 секунд
            const retryInterval = 300; // проверяем каждые 300ms
            
            const checkInterval = setInterval(() => {
                attempts++;
                console.log(`Attempt ${attempts}/${maxAttempts} - Checking for TronWeb...`);
                
                if (typeof window.tronWeb !== 'undefined') {
                    console.log('✅ TronWeb detected!');
                    clearInterval(checkInterval);
                    this.checkTronWeb();
                } else if (attempts >= maxAttempts) {
                    console.log('❌ TronWeb not found after all attempts');
                    clearInterval(checkInterval);
                    this.checkTronWeb(); // Финальная проверка
                }
            }, retryInterval);
        },
        
        /**
         * Check if TronWeb is available
         */
        checkTronWeb() {
            console.log('=== TronAuth: Checking TronWeb ===');
            console.log('window.tronWeb exists:', typeof window.tronWeb !== 'undefined');
            console.log('window.tronWeb:', window.tronWeb);
            
            // Проверяем только наличие tronWeb (без strict ready check для совместимости с TrustWallet)
            if (typeof window.tronWeb !== 'undefined') {
                console.log('TronWeb detected!');
                this.isTronWebAvailable = true;
                
                // Проверяем, подключен ли кошелек к сайту
                const isConnected = window.tronWeb.defaultAddress && 
                                   window.tronWeb.defaultAddress.base58 &&
                                   window.tronWeb.defaultAddress.base58 !== false;
                
                console.log('Is connected:', isConnected);
                
                if (isConnected) {
                    this.showStatus('TronLink или TrustWallet подключен', 'success');
                } else {
                    this.showStatus('TronLink или TrustWallet обнаружен. Нажмите "Подключить" для авторизации.', 'info');
                }
            } else if (this.isMobileDevice) {
                console.log('Mobile device, will use WalletConnect');
                // На мобильных устройствах будем использовать WalletConnect
                this.useWalletConnect = true;
                this.isTronWebAvailable = true; // Разрешаем подключение через WC
            } else {
                console.log('TronWeb not found');
                this.showStatus('Установите TronLink или TrustWallet', 'info');
            }
            
            console.log('isTronWebAvailable:', this.isTronWebAvailable);
        },
        
        /**
         * Get nonce from backend
         */
        async getNonce(address) {
            try {
                const response = await fetch(`${this.apiBase}/auth/tron/nonce`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ wallet_address: address })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to get nonce');
                }

                const data = await response.json();
                return data;
            } catch (error) {
                this.showStatus(`Ошибка получения nonce: ${error.message}`, 'error');
                throw error;
            }
        },
        
        /**
         * Sign message with TronWeb
         */
        async signMessage(message, address) {
            try {
                const signature = await window.tronWeb.trx.sign(message);
                return signature;
            } catch (error) {
                if (error.message && error.message.includes('Confirmation declined')) {
                    this.showStatus('Подпись сообщения отклонена.', 'error');
                } else {
                    this.showStatus(`Ошибка подписи: ${error.message}`, 'error');
                }
                throw error;
            }
        },
        
        /**
         * Verify signature and get JWT token
         */
        async verifySignature(address, signature, message) {
            try {
                const response = await fetch(`${this.apiBase}/auth/tron/verify`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        wallet_address: address,
                        signature: signature,
                        message: message
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to verify signature');
                }

                const data = await response.json();
                return data.token;
            } catch (error) {
                this.showStatus(`Ошибка проверки подписи: ${error.message}`, 'error');
                throw error;
            }
        },
        
        /**
         * Store token in cookie
         */
        storeToken(token) {
            const expires = new Date();
            expires.setTime(expires.getTime() + 24 * 60 * 60 * 1000);
            document.cookie = `tron_auth_token=${token}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
        },
        
        /**
         * Remove token from cookie
         */
        removeToken() {
            document.cookie = 'tron_auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        },
        
        /**
         * Connect directly via TronLink/TrustWallet
         */
        async connectDirectly() {
            if (!window.tronWeb) {
                this.showStatus('Кошелек не обнаружен', 'error');
                return;
            }
            
            try {
                this.isConnecting = true;
                console.log('Attempting to connect to TRON wallet...');
                
                // TrustWallet/TronLink могут требовать явного запроса разрешения
                // Пробуем разные методы запроса доступа
                
                // Метод 1: Через tronWeb.request (современный API)
                if (window.tronWeb.request) {
                    try {
                        console.log('Trying tronWeb.request...');
                        const accounts = await window.tronWeb.request({ 
                            method: 'tron_requestAccounts' 
                        });
                        console.log('Request result:', accounts);
                    } catch (requestError) {
                        console.log('tronWeb.request failed:', requestError);
                    }
                }
                
                // Метод 2: Проверяем tronLink API (для TronLink расширения)
                if (window.tronLink && !window.tronLink.ready) {
                    try {
                        console.log('Requesting tronLink...');
                        const res = await window.tronLink.request({ method: 'tron_requestAccounts' });
                        console.log('tronLink.request result:', res);
                    } catch (e) {
                        console.log('tronLink.request failed:', e);
                    }
                }
                
                // Даем время кошельку обновиться
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Пробуем получить адрес из разных источников
                let address = null;
                
                // Источник 1: window.tronWeb.defaultAddress
                if (window.tronWeb.defaultAddress?.base58 && 
                    window.tronWeb.defaultAddress.base58 !== false) {
                    address = window.tronWeb.defaultAddress.base58;
                    console.log('Address from tronWeb.defaultAddress:', address);
                }
                
                // Источник 2: window.tronLink.tronWeb (для TronLink)
                if (!address && window.tronLink?.tronWeb?.defaultAddress?.base58) {
                    address = window.tronLink.tronWeb.defaultAddress.base58;
                    console.log('Address from tronLink.tronWeb:', address);
                }
                
                // Источник 3: Прямой запрос через tronWeb
                if (!address) {
                    try {
                        // Некоторые кошельки могут иметь метод для получения адресов
                        if (typeof window.tronWeb.trx?.getAccount === 'function') {
                            console.log('Trying tronWeb.trx.getAccount...');
                        }
                    } catch (e) {
                        console.log('Failed to get account:', e);
                    }
                }
                
                if (!address) {
                    console.error('Could not get wallet address. Please unlock wallet and refresh the page.');
                    this.showStatus('Разблокируйте кошелек TrustWallet, обновите страницу и попробуйте снова', 'error');
                    return;
                }
                
                console.log('Successfully got address:', address);
                this.walletAddress = address;
                
                // Get nonce from backend
                this.showStatus('Получение запроса на авторизацию...', 'info');
                const { nonce, message } = await this.getNonce(address);
                
                // Sign message
                this.showStatus('Подпишите сообщение в кошельке...', 'info');
                const signature = await this.signMessage(message, address);
                
                // Verify signature
                this.showStatus('Проверка подписи...', 'info');
                const token = await this.verifySignature(address, signature, message);
                
                // Store token
                this.storeToken(token);
                this.isAuthenticated = true;
                
                // Emit authenticated event for parent components
                this.$emit('authenticated', this.walletAddress, token);
                
                this.showStatus('Успешно авторизован!', 'success');
                
            } catch (error) {
                console.error('Connection error:', error);
                this.walletAddress = null;
                this.isAuthenticated = false;
            } finally {
                this.isConnecting = false;
            }
        },
        
        /**
         * Connect via WalletConnect (for mobile)
         */
        async connectViaWalletConnect() {
            try {
                this.isConnecting = true;
                this.showStatus('Инициализация WalletConnect...', 'info');
                
                // Check if WalletConnect is available
                if (typeof WalletConnectProvider === 'undefined') {
                    this.showStatus('WalletConnect не загружен. Используйте прямое подключение.', 'error');
                    return;
                }
                
                const provider = new WalletConnectProvider.default({
                    rpc: {
                        728126428: "https://api.trongrid.io"
                    },
                    chainId: 728126428,
                    qrcode: true,
                    qrcodeModalOptions: {
                        mobileLinks: [
                            "metamask",
                            "trust",
                            "rainbow",
                        ]
                    }
                });
                
                // Enable provider (shows QR code)
                await provider.enable();
                
                this.walletConnectProvider = provider;
                const accounts = provider.accounts;
                
                if (accounts && accounts.length > 0) {
                    const address = accounts[0];
                    this.walletAddress = address;
                    
                    // Get nonce and authorize
                    const { nonce, message } = await this.getNonce(address);
                    
                    // Sign through WalletConnect
                    const signature = await this.signMessageViaWalletConnect(message);
                    
                    const token = await this.verifySignature(address, signature, message);
                    
                    this.storeToken(token);
                    this.isAuthenticated = true;
                    this.showStatus('Успешно авторизован через WalletConnect!', 'success');
                }
                
            } catch (error) {
                console.error('WalletConnect error:', error);
                this.showStatus(`Ошибка WalletConnect: ${error.message}`, 'error');
            } finally {
                this.isConnecting = false;
            }
        },
        
        /**
         * Sign message via WalletConnect
         */
        async signMessageViaWalletConnect(message) {
            if (!this.walletConnectProvider) {
                throw new Error('WalletConnect не инициализирован');
            }
            
            const signature = await this.walletConnectProvider.request({
                method: 'tron_signMessage',
                params: [message, this.walletAddress]
            });
            
            return signature;
        },
        
        /**
         * Universal connect method
         */
        async connect() {
            this.hideStatus();
            
            // Determine connection method
            if (this.isMobileDevice && !window.tronWeb) {
                // Use WalletConnect for mobile without extension
                await this.connectViaWalletConnect();
            } else if (window.tronWeb) {
                // Use direct connection via TronLink/TrustWallet (убрана проверка ready)
                await this.connectDirectly();
            } else {
                this.showStatus('Установите TronLink или TrustWallet для продолжения', 'error');
            }
        },
        
        /**
         * Disconnect wallet
         */
        disconnect() {
            if (this.walletConnectProvider) {
                try {
                    this.walletConnectProvider.disconnect();
                } catch (e) {
                    console.error('Error disconnecting WalletConnect:', e);
                }
            }
            
            this.walletAddress = null;
            this.isAuthenticated = false;
            this.removeToken();
            this.showStatus('Отключено', 'info');
            this.signature = '';
            this.messageToSign = '';
            this.waitingForCallback = false;
        },
        
        /**
         * Sign arbitrary text
         */
        async signText() {
            console.log('=== signText called ===');
            console.log('isAuthenticated:', this.isAuthenticated);
            console.log('walletAddress:', this.walletAddress);
            console.log('window.tronWeb exists:', typeof window.tronWeb !== 'undefined');
            console.log('window.tronWeb:', window.tronWeb);
            
            if (!this.isAuthenticated) {
                this.showStatus('Сначала подключитесь и авторизуйтесь', 'error');
                return;
            }

            const text = this.messageToSign.trim();
            
            if (!text) {
                this.showStatus('Введите текст для подписи', 'error');
                return;
            }

            try {
                this.isSigning = true;
                this.hideStatus();

                this.showStatus('Подпишите сообщение в кошельке...', 'info');

                // Sign message - проверяем наличие tronWeb без проверки ready
                let signature;
                if (window.tronWeb) {
                    console.log('Using window.tronWeb for signing');
                    try {
                        signature = await window.tronWeb.trx.sign(text);
                        console.log('Signature received:', signature);
                    } catch (signError) {
                        console.error('TronWeb sign error:', signError);
                        throw signError;
                    }
                } else if (this.walletConnectProvider) {
                    console.log('Using WalletConnect for signing');
                    signature = await this.signMessageViaWalletConnect(text);
                } else {
                    console.error('No wallet available for signing');
                    this.showStatus('Кошелек не подключен', 'error');
                    return;
                }

                this.signature = signature;
                this.showStatus('Сообщение подписано!', 'success');

            } catch (error) {
                console.error('Signing error:', error);
                if (error.message && error.message.includes('declined')) {
                    this.showStatus('Подпись отклонена.', 'error');
                } else {
                    this.showStatus(`Ошибка подписи: ${error.message}`, 'error');
                }
                this.signature = '';
            } finally {
                this.isSigning = false;
            }
        },
        
        /**
         * Handle keydown event for message input
         */
        handleKeyDown(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.signText();
            }
        },
        
        /**
         * Check if user is already authenticated
         */
        async checkExistingAuth() {
            const cookies = document.cookie.split(';');
            const tokenCookie = cookies.find(c => c.trim().startsWith('tron_auth_token='));
            
            if (tokenCookie) {
                const token = tokenCookie.split('=')[1];
                try {
                    const response = await fetch(`${this.apiBase}/auth/tron/me`, {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (response.ok) {
                        const userInfo = await response.json();
                        this.walletAddress = userInfo.wallet_address;
                        this.isAuthenticated = true;
                        return;
                    }
                } catch (error) {
                    console.error('Error checking auth:', error);
                }
            }

            // If no valid token, check if TronWeb is already connected
            if (window.tronWeb) {
                try {
                    const address = window.tronWeb.defaultAddress?.base58;
                    if (address && address !== false) {
                        this.walletAddress = address;
                    }
                } catch (error) {
                    console.error('Error checking TronWeb:', error);
                }
            }
        }
    },
    
    template: `
        <div :class="isMobileDevice ? 'web3-auth-mobile' : 'web3-auth-container'">
            <div :class="isMobileDevice ? 'mobile-container' : 'container'">
                <div :class="isMobileDevice ? 'mobile-header' : ''">
                    <h1>🔐 TRON Authentication</h1>
                    <p :class="isMobileDevice ? 'mobile-subtitle' : 'subtitle'">
                        Подключитесь через TRON кошелек
                    </p>
                </div>

                <div v-if="statusVisible" :class="isMobileDevice ? ['mobile-status', statusType] : ['status', statusType]">
                    [[ statusMessage ]]
                </div>

                <div v-if="!isAuthenticated" :class="isMobileDevice ? 'mobile-not-connected' : 'not-connected'">
                    <button 
                        :class="isMobileDevice ? 'mobile-btn mobile-btn-primary' : ''"
                        :id="!isMobileDevice ? 'connect-btn' : ''"
                        @click="connect"
                        :disabled="isConnecting || (!isTronWebAvailable && !useWalletConnect)"
                    >
                        <span v-if="isConnecting" :class="isMobileDevice ? 'mobile-loading' : 'loading'"></span>
                        [[ isConnecting ? 'Подключение...' : 'Подключить TRON кошелек' ]]
                    </button>
                    <p :class="isMobileDevice ? 'mobile-hint' : ''" style="color: #999; font-size: 12px; margin-top: 20px;">
                        <template v-if="!isMobileDevice">
                            Убедитесь, что TronLink или TrustWallet установлен и разблокирован
                        </template>
                        <template v-else>
                            Нажмите кнопку для подключения через мобильный кошелек
                        </template>
                    </p>
                </div>

                <div v-else :class="isMobileDevice ? 'mobile-connected' : ''">
                    <div v-if="isMobileDevice" class="mobile-user-card">
                        <div class="mobile-user-header">
                            <div class="mobile-user-icon">✓</div>
                            <div class="mobile-user-info">
                                <div class="mobile-user-label">Подключено</div>
                                <div class="mobile-user-address">[[ shortAddress ]]</div>
                            </div>
                        </div>
                        <button class="mobile-btn mobile-btn-secondary" @click="disconnect">
                            Отключить
                        </button>
                    </div>
                    
                    <div v-if="!isMobileDevice">
                        <button id="disconnect-btn" class="secondary" @click="disconnect">
                            Отключить
                        </button>
                        
                        <div class="user-info">
                            <h3>Авторизован</h3>
                            <p><strong>TRON адрес:</strong> [[ walletAddress ]]</p>
                            <p><strong>Статус:</strong> <span>Авторизован</span></p>
                        </div>
                    </div>

                    <div :class="isMobileDevice ? 'mobile-section' : 'sign-section'">
                        <h3 v-if="!isMobileDevice">✍️ Подписать сообщение</h3>
                        <div v-if="isMobileDevice">
                            <div class="mobile-section-header" style="background: transparent; cursor: default; padding: 16px 0;">
                                <span>✍️ Подписать сообщение</span>
                            </div>
                            <div class="mobile-section-content" style="display: block;">
                                <textarea
                                    v-model="messageToSign"
                                    class="mobile-textarea"
                                    placeholder="Введите текст для подписи..."
                                    @keydown="handleKeyDown"
                                ></textarea>
                                <button 
                                    class="mobile-btn mobile-btn-primary"
                                    @click="signText"
                                    :disabled="isSigning || !messageToSign.trim()"
                                >
                                    <span v-if="isSigning" class="mobile-loading"></span>
                                    [[ isSigning ? 'Подписание...' : 'Подписать' ]]
                                </button>
                                <div v-if="signature" class="mobile-signature">
                                    <div class="mobile-signature-label">Подпись:</div>
                                    <div class="mobile-signature-value">[[ signature ]]</div>
                                </div>
                            </div>
                        </div>
                        <template v-else>
                            <label for="tron-message-input">Введите текст для подписи:</label>
                            <textarea
                                id="tron-message-input"
                                v-model="messageToSign"
                                placeholder="Введите любое сообщение для подписи вашим кошельком..."
                                @keydown="handleKeyDown"
                            ></textarea>
                            <button 
                                id="sign-btn"
                                @click="signText"
                                :disabled="isSigning || !messageToSign.trim()"
                            >
                                <span v-if="isSigning" class="loading"></span>
                                [[ isSigning ? 'Подписание...' : 'Подписать с TRON' ]]
                            </button>
                            <div v-if="signature" class="signature-result">
                                <strong>Подпись:</strong>
                                <div>[[ signature ]]</div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>
    `
});

// AdminAccount Component
Vue.component('AdminAccount', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true,
            error: null,
            adminInfo: null,
            
            // Change password
            changingPassword: false,
            oldPassword: '',
            newPassword: '',
            confirmPassword: '',
            passwordError: null,
            passwordSuccess: null,
            
            // Change TRON address
            changingTron: false,
            newTronAddress: '',
            tronError: null,
            tronSuccess: null,
            
            // TRON addresses list
            tronAddresses: [],
            loadingTronAddresses: false,
            addingTronAddress: false,
            newTronAddressToAdd: '',
            addTronError: null,
            addTronSuccess: null,
            editingTronId: null,
            editTronAddress: '',
            deletingTronId: null
        };
    },
    mounted() {
        this.loadAdminInfo();
        this.loadTronAddresses();
    },
    methods: {
        async loadAdminInfo() {
            this.loading = true;
            this.error = null;
            try {
                const response = await fetch('/api/admin/info');
                
                if (!response.ok) {
                    if (response.status === 404) {
                        this.error = 'Администратор не настроен';
                        return;
                    }
                    
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        this.error = errorData.detail || 'Ошибка загрузки информации';
                    } else {
                        this.error = `Ошибка ${response.status}: ${response.statusText}`;
                    }
                    return;
                }
                
                this.adminInfo = await response.json();
            } catch (error) {
                console.error('Error loading admin info:', error);
                this.error = error.message || 'Ошибка загрузки информации';
            } finally {
                this.loading = false;
            }
        },
        
        async changePassword() {
            // Validate inputs
            if (!this.oldPassword || !this.newPassword || !this.confirmPassword) {
                this.passwordError = 'Все поля обязательны для заполнения';
                return;
            }
            
            if (this.newPassword !== this.confirmPassword) {
                this.passwordError = 'Новые пароли не совпадают';
                return;
            }
            
            if (this.newPassword.length < 8) {
                this.passwordError = 'Пароль должен содержать минимум 8 символов';
                return;
            }
            
            this.passwordError = null;
            this.passwordSuccess = null;
            this.changingPassword = true;
            
            try {
                const response = await fetch('/api/admin/change-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        old_password: this.oldPassword,
                        new_password: this.newPassword
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    this.passwordError = data.detail || 'Ошибка смены пароля';
                    return;
                }
                
                this.passwordSuccess = 'Пароль успешно изменен';
                this.oldPassword = '';
                this.newPassword = '';
                this.confirmPassword = '';
                
                // Reload admin info
                await this.loadAdminInfo();
                
                // Clear success message after 3 seconds
                setTimeout(() => {
                    this.passwordSuccess = null;
                }, 3000);
            } catch (error) {
                console.error('Error changing password:', error);
                this.passwordError = error.message || 'Ошибка смены пароля';
            } finally {
                this.changingPassword = false;
            }
        },
        
        // OLD METHOD - REMOVED: changeTronAddress() - now using list management
        
        async loadTronAddresses() {
            this.loadingTronAddresses = true;
            try {
                const response = await fetch('/api/admin/tron-addresses');
                if (response.ok) {
                    const data = await response.json();
                    this.tronAddresses = data.addresses || [];
                }
            } catch (error) {
                console.error('Error loading TRON addresses:', error);
            } finally {
                this.loadingTronAddresses = false;
            }
        },
        
        async addTronAddress() {
            if (!this.newTronAddressToAdd) {
                this.addTronError = 'Введите TRON адрес';
                return;
            }
            
            if (!this.newTronAddressToAdd.startsWith('T') || this.newTronAddressToAdd.length !== 34) {
                this.addTronError = 'Неверный формат TRON адреса';
                return;
            }
            
            this.addTronError = null;
            this.addTronSuccess = null;
            this.addingTronAddress = true;
            
            try {
                const response = await fetch('/api/admin/tron-addresses', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({tron_address: this.newTronAddressToAdd})
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    this.addTronError = data.detail || 'Ошибка добавления адреса';
                    return;
                }
                
                this.addTronSuccess = 'TRON адрес добавлен';
                this.newTronAddressToAdd = '';
                await this.loadTronAddresses();
                await this.loadAdminInfo(); // Refresh admin info to update tron_addresses_count
                
                setTimeout(() => {
                    this.addTronSuccess = null;
                }, 3000);
            } catch (error) {
                console.error('Error adding TRON address:', error);
                this.addTronError = error.message || 'Ошибка добавления адреса';
            } finally {
                this.addingTronAddress = false;
            }
        },
        
        startEditTron(item) {
            this.editingTronId = item.id;
            this.editTronAddress = item.tron_address;
        },
        
        cancelEditTron() {
            this.editingTronId = null;
            this.editTronAddress = '';
        },
        
        async saveTronAddress(item) {
            if (!this.editTronAddress || !this.editTronAddress.startsWith('T') || this.editTronAddress.length !== 34) {
                return;
            }
            
            try {
                const response = await fetch(`/api/admin/tron-addresses/${item.id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({tron_address: this.editTronAddress})
                });
                
                if (response.ok) {
                    this.editingTronId = null;
                    this.editTronAddress = '';
                    await this.loadTronAddresses();
                    await this.loadAdminInfo(); // Refresh admin info to update tron_addresses_count
                }
            } catch (error) {
                console.error('Error updating TRON address:', error);
            }
        },
        
        async deleteTronAddress(item) {
            if (!confirm(`Удалить TRON адрес ${item.tron_address}?`)) {
                return;
            }
            
            this.deletingTronId = item.id;
            
            try {
                const response = await fetch(`/api/admin/tron-addresses/${item.id}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    alert(data.detail || 'Ошибка удаления');
                    return;
                }
                
                await this.loadTronAddresses();
                await this.loadAdminInfo(); // Refresh admin info to update tron_addresses_count
            } catch (error) {
                console.error('Error deleting TRON address:', error);
                alert('Ошибка удаления адреса');
            } finally {
                this.deletingTronId = null;
            }
        },
        
        formatDate(dateString) {
            if (!dateString) return 'N/A';
            const date = new Date(dateString);
            return date.toLocaleString('ru-RU', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    },
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fas fa-user-shield me-1"></i>
                Администрирование аккаунта
            </div>
            <div class="card-body">
                <div v-if="loading" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                    <p class="mt-2">Загрузка информации...</p>
                </div>
                
                <div v-else-if="error" class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    [[ error ]]
                </div>
                
                <div v-else-if="adminInfo">
                    <!-- Admin Info -->
                    <div class="mb-4">
                        <h5 class="mb-3">
                            <i class="fas fa-info-circle me-2 text-primary"></i>
                            Информация об аккаунте
                        </h5>
                        
                        <div class="row mb-2">
                            <div class="col-md-4 fw-bold">Методы аутентификации:</div>
                            <div class="col-md-8">
                                <span v-if="adminInfo.has_password" class="badge bg-primary me-2">
                                    <i class="fas fa-key me-1"></i> Пароль
                                </span>
                                <span v-if="adminInfo.tron_addresses_count > 0" class="badge bg-info">
                                    <i class="fas fa-wallet me-1"></i> TRON ([[ adminInfo.tron_addresses_count ]])
                                </span>
                                <span v-if="!adminInfo.has_password && adminInfo.tron_addresses_count === 0" class="badge bg-warning">
                                    <i class="fas fa-exclamation-triangle me-1"></i> Не настроено
                                </span>
                            </div>
                        </div>
                        
                        <div v-if="adminInfo.username" class="row mb-2">
                            <div class="col-md-4 fw-bold">Имя пользователя:</div>
                            <div class="col-md-8">[[ adminInfo.username ]]</div>
                        </div>
                        
                        <div v-if="adminInfo.tron_address" class="row mb-2">
                            <div class="col-md-4 fw-bold">TRON адрес:</div>
                            <div class="col-md-8">
                                <code>[[ adminInfo.tron_address ]]</code>
                            </div>
                        </div>
                        
                        <div class="row mb-2">
                            <div class="col-md-4 fw-bold">Создан:</div>
                            <div class="col-md-8">[[ formatDate(adminInfo.created_at) ]]</div>
                        </div>
                        
                        <div class="row mb-2">
                            <div class="col-md-4 fw-bold">Обновлен:</div>
                            <div class="col-md-8">[[ formatDate(adminInfo.updated_at) ]]</div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-4 fw-bold">Статус:</div>
                            <div class="col-md-8">
                                <span v-if="adminInfo.has_password || adminInfo.tron_addresses_count > 0" class="badge bg-success">
                                    <i class="fas fa-check-circle me-1"></i> Активен
                                </span>
                                <span v-else class="badge bg-warning">
                                    <i class="fas fa-exclamation-triangle me-1"></i> Не настроен
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <hr>
                    
                    <!-- Change Password (if password is configured) -->
                    <div v-if="adminInfo.has_password" class="mb-4">
                        <h5 class="mb-3">
                            <i class="fas fa-lock me-2 text-warning"></i>
                            Сменить пароль
                        </h5>
                        
                        <div v-if="passwordError" class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            [[ passwordError ]]
                        </div>
                        
                        <div v-if="passwordSuccess" class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i>
                            [[ passwordSuccess ]]
                        </div>
                        
                        <div class="row g-3">
                            <div class="col-md-12">
                                <label class="form-label">Старый пароль</label>
                                <input 
                                    type="password" 
                                    class="form-control" 
                                    v-model="oldPassword"
                                    placeholder="Введите текущий пароль"
                                    :disabled="changingPassword"
                                />
                            </div>
                            
                            <div class="col-md-6">
                                <label class="form-label">Новый пароль</label>
                                <input 
                                    type="password" 
                                    class="form-control" 
                                    v-model="newPassword"
                                    placeholder="Минимум 8 символов"
                                    :disabled="changingPassword"
                                />
                            </div>
                            
                            <div class="col-md-6">
                                <label class="form-label">Подтвердите новый пароль</label>
                                <input 
                                    type="password" 
                                    class="form-control" 
                                    v-model="confirmPassword"
                                    placeholder="Повторите новый пароль"
                                    :disabled="changingPassword"
                                />
                            </div>
                            
                            <div class="col-12">
                                <button 
                                    class="btn btn-primary"
                                    @click="changePassword"
                                    :disabled="changingPassword || !oldPassword || !newPassword || !confirmPassword"
                                >
                                    <span v-if="changingPassword" class="spinner-border spinner-border-sm me-2"></span>
                                    [[ changingPassword ? 'Смена пароля...' : 'Сменить пароль' ]]
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Old TRON address change - REMOVED, now using list management below -->
                    <div v-if="false" class="mb-4">
                        <h5 class="mb-3">
                            <i class="fas fa-wallet me-2 text-info"></i>
                            Сменить TRON адрес
                        </h5>
                        
                        <div v-if="tronError" class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            [[ tronError ]]
                        </div>
                        
                        <div v-if="tronSuccess" class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i>
                            [[ tronSuccess ]]
                        </div>
                        
                        <div class="row g-3">
                            <div class="col-12">
                                <label class="form-label">Новый TRON адрес</label>
                                <input 
                                    type="text" 
                                    class="form-control" 
                                    v-model="newTronAddress"
                                    placeholder="T..."
                                    :disabled="changingTron"
                                />
                                <small class="form-text text-muted">
                                    Введите новый TRON адрес для доступа к админ-панели
                                </small>
                            </div>
                            
                            <div class="col-12">
                                <button 
                                    class="btn btn-info text-white"
                                    @click="changeTronAddress"
                                    :disabled="changingTron || !newTronAddress"
                                >
                                    <span v-if="changingTron" class="spinner-border spinner-border-sm me-2"></span>
                                    [[ changingTron ? 'Смена адреса...' : 'Сменить TRON адрес' ]]
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- TRON Addresses Management -->
                    <div class="mb-4">
                        <h5 class="mb-3">
                            <i class="fas fa-list me-2 text-info"></i>
                            Управление TRON адресами
                        </h5>
                        
                        <!-- Add new TRON address -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <h6 class="card-title">Добавить TRON адрес</h6>
                                
                                <div v-if="addTronError" class="alert alert-danger alert-sm">
                                    <i class="fas fa-exclamation-circle me-2"></i>
                                    [[ addTronError ]]
                                </div>
                                
                                <div v-if="addTronSuccess" class="alert alert-success alert-sm">
                                    <i class="fas fa-check-circle me-2"></i>
                                    [[ addTronSuccess ]]
                                </div>
                                
                                <div class="row g-2">
                                    <div class="col-md-9">
                                        <input 
                                            type="text" 
                                            class="form-control" 
                                            v-model="newTronAddressToAdd"
                                            placeholder="T..."
                                            :disabled="addingTronAddress"
                                        />
                                    </div>
                                    <div class="col-md-3">
                                        <button 
                                            class="btn btn-primary w-100"
                                            @click="addTronAddress"
                                            :disabled="addingTronAddress || !newTronAddressToAdd"
                                        >
                                            <span v-if="addingTronAddress" class="spinner-border spinner-border-sm me-1"></span>
                                            <i v-else class="fas fa-plus me-1"></i>
                                            Добавить
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- List of TRON addresses -->
                        <div v-if="loadingTronAddresses" class="text-center py-3">
                            <div class="spinner-border spinner-border-sm text-primary"></div>
                            <span class="ms-2">Загрузка...</span>
                        </div>
                        
                        <div v-else-if="tronAddresses.length === 0" class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Нет добавленных TRON адресов
                        </div>
                        
                        <div v-else class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>TRON Адрес</th>
                                        <th>Добавлен</th>
                                        <th>Статус</th>
                                        <th width="120">Действия</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="item in tronAddresses" :key="item.id">
                                        <td>
                                            <span v-if="editingTronId !== item.id">
                                                <code>[[ item.tron_address ]]</code>
                                            </span>
                                            <input 
                                                v-else
                                                type="text" 
                                                class="form-control form-control-sm" 
                                                v-model="editTronAddress"
                                            />
                                        </td>
                                        <td>[[ formatDate(item.created_at) ]]</td>
                                        <td>
                                            <span v-if="item.is_active" class="badge bg-success">
                                                <i class="fas fa-check-circle me-1"></i> Активен
                                            </span>
                                            <span v-else class="badge bg-secondary">Неактивен</span>
                                        </td>
                                        <td>
                                            <div v-if="editingTronId !== item.id" class="btn-group btn-group-sm">
                                                <button 
                                                    class="btn btn-outline-primary"
                                                    @click="startEditTron(item)"
                                                    title="Редактировать"
                                                >
                                                    <i class="fas fa-edit"></i>
                                                </button>
                                                <button 
                                                    class="btn btn-outline-danger"
                                                    @click="deleteTronAddress(item)"
                                                    :disabled="deletingTronId === item.id"
                                                    title="Удалить"
                                                >
                                                    <span v-if="deletingTronId === item.id" class="spinner-border spinner-border-sm"></span>
                                                    <i v-else class="fas fa-trash"></i>
                                                </button>
                                            </div>
                                            <div v-else class="btn-group btn-group-sm">
                                                <button 
                                                    class="btn btn-success"
                                                    @click="saveTronAddress(item)"
                                                    title="Сохранить"
                                                >
                                                    <i class="fas fa-check"></i>
                                                </button>
                                                <button 
                                                    class="btn btn-secondary"
                                                    @click="cancelEditTron"
                                                    title="Отмена"
                                                >
                                                    <i class="fas fa-times"></i>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <hr>
                    
                    <!-- Security Notice -->
                    <div class="alert alert-info">
                        <i class="fas fa-shield-alt me-2"></i>
                        <strong>Безопасность:</strong> Убедитесь, что вы находитесь в безопасном месте при изменении учетных данных.
                        После смены пароля или TRON адреса вам потребуется повторная авторизация.
                    </div>
                </div>
            </div>
        </div>
    `
});