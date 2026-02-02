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
            error: null
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
                if (!response.ok) {
                    if (response.status === 404) {
                        this.error = 'Нода не инициализирована';
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Ошибка загрузки информации о ключе');
                    }
                } else {
                    this.keyInfo = await response.json();
                }
            } catch (error) {
                console.error('Error loading key info:', error);
                this.error = error.message || 'Ошибка загрузки информации о ключе';
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
        }
    },
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fa-regular fa-address-card me-1"></i>
                Профиль ноды
            </div>
            <div class="card-body">
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
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label fw-bold">
                                <i class="fas fa-wallet me-2"></i>
                                Ethereum Адрес:
                            </label>
                            <div class="input-group">
                                <input 
                                    type="text" 
                                    class="form-control font-monospace" 
                                    :value="keyInfo.address" 
                                    readonly
                                    style="font-size: 0.9rem;"
                                />
                                <button 
                                    class="btn btn-outline-secondary" 
                                    type="button"
                                    @click="copyToClipboard(keyInfo.address)"
                                    title="Копировать адрес">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label class="form-label fw-bold">
                                <i class="fas fa-info-circle me-2"></i>
                                Тип ключа:
                            </label>
                            <input 
                                type="text" 
                                class="form-control" 
                                :value="keyInfo.key_type" 
                                readonly
                            />
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">
                            <i class="fas fa-key me-2"></i>
                            Публичный ключ (hex):
                        </label>
                        <div class="input-group">
                            <textarea 
                                class="form-control font-monospace" 
                                rows="2"
                                :value="keyInfo.public_key" 
                                readonly
                                style="font-size: 0.85rem;"
                            ></textarea>
                            <button 
                                class="btn btn-outline-secondary" 
                                type="button"
                                @click="copyToClipboard(keyInfo.public_key)"
                                title="Копировать публичный ключ">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
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
                    
                    <div class="alert alert-info mt-4">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Информация:</strong> Публичный ключ и PEM можно безопасно делиться с другими. 
                        Они используются для проверки подписей и шифрования сообщений для вас.
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
            currentMethod: 'mnemonic',
            mnemonicInput: '',
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
            pemContent: ''
        };
    },
    mounted() {
        // Check if node needs initialization
        const initScript = document.getElementById('is-node-initialized');
        if (initScript) {
            const initialized = JSON.parse(initScript.textContent);
            if (!initialized) {
                this.show = true;
                this.$nextTick(() => {
                    this.initCanvas();
                });
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
                this.showStatus('Ключ успешно сохранен! Скопируйте данные и закройте окно.', 'success');
                // Убрать автоматическую перезагрузку
                // Пользователь сам закроет окно через кнопку "Закрыть"
            } catch (error) {
                console.error('Error:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
            }
        },
        resetForm() {
            this.mnemonicInput = '';
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
        async generateFromMnemonic() {
            if (!this.mnemonicInput.trim()) {
                this.showStatus('Введите мнемоническую фразу', 'error');
                return;
            }

            try {
                this.showStatus('Создание ключа...', 'info');
                const words = this.mnemonicInput.trim().split(/\s+/).filter(w => w.length > 0);
                
                if (words.length !== 12 && words.length !== 24) {
                    throw new Error('Мнемоническая фраза должна содержать 12 или 24 слова');
                }

                // Check if ethers is available
                if (typeof ethers === 'undefined') {
                    throw new Error('Ethers.js не загружен. Пожалуйста, обновите страницу.');
                }

                const wallet = ethers.Wallet.fromMnemonic(words.join(' '));
                this.result = {
                    address: wallet.address,
                    privateKey: wallet.privateKey,
                    mnemonic: words.join(' ')
                };
                
                // Save to server
                await this.saveMnemonic(words.join(' '));
                
                this.showStatus('Ключ успешно создан!', 'success');
            } catch (error) {
                console.error('Error:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
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
            this.entropyProgress = Math.min(100, (estimatedBytes / this.requiredEntropy) * 100);
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
                
                // Don't auto-reload, let user close manually after copying data
                this.showStatus('Ключ успешно сохранен! Скопируйте данные и закройте окно.', 'success');
                // Убрать автоматическую перезагрузку
                // Пользователь сам закроет окно через кнопку "Закрыть"
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
        closeModal() {
            // If result exists, node is initialized, so reload page
            if (this.result) {
                this.show = false;
                location.reload();
            } else {
                // Prevent closing if not initialized
                this.showStatus('Необходимо инициализировать ноду перед продолжением', 'error');
            }
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
                <h3>🔑 Инициализация ноды</h3>
            </template>
            <template #body>
                <div v-if="status.visible" :class="'alert alert-' + (status.type === 'error' ? 'danger' : status.type === 'success' ? 'success' : 'info')" style="border-radius: 10px; margin-bottom: 20px;">
                    [[ status.message ]]
                </div>
                
                <p class="seed-modal-intro">Для работы ноды необходимо создать мнемоническую фразу или загрузить ключ</p>
                
                <div class="method-selector">
                    <button type="button" 
                            :class="'method-btn ' + (currentMethod === 'mnemonic' ? 'active' : '')"
                            @click="switchMethod('mnemonic')">
                        📝 Мнемоническая фраза
                    </button>
                    <button type="button" 
                            :class="'method-btn ' + (currentMethod === 'mouse' ? 'active' : '')"
                            @click="switchMethod('mouse')">
                        🖱️ Движение мышкой
                    </button>
                    <button type="button" 
                            :class="'method-btn ' + (currentMethod === 'pem' ? 'active' : '')"
                            @click="switchMethod('pem')">
                        📄 PEM файл
                    </button>
                </div>
                
                <!-- Mnemonic Method -->
                <div v-if="currentMethod === 'mnemonic'" class="method-content">
                    <div class="alert alert-warning" style="border-radius: 10px; border-left: 4px solid #ffc107;">
                        <strong>⚠️ Внимание!</strong> Никогда не делитесь своей мнемонической фразой с третьими лицами.
                    </div>
                    <div class="seed-form-group">
                        <label for="mnemonic-input" class="seed-form-label">Введите мнемоническую фразу (12 или 24 слова):</label>
                        <textarea 
                            id="mnemonic-input"
                            v-model="mnemonicInput"
                            class="form-control seed-textarea"
                            rows="4"
                            placeholder="word1 word2 word3 ... word12"
                        ></textarea>
                    </div>
                    <button class="seed-btn-primary" @click="generateFromMnemonic">
                        Создать ключ из мнемоники
                    </button>
                </div>
                
                <!-- Mouse Method -->
                <div v-if="currentMethod === 'mouse'" class="method-content">
                    <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                        <strong>ℹ️ Информация</strong> Двигайте мышкой по области ниже для генерации энтропии.
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
                        class="seed-btn-primary" 
                        :disabled="!canGenerateFromMouse"
                        @click="generateFromMouseEntropy">
                        Создать ключ из энтропии
                    </button>
                </div>
                        
                <!-- PEM Method -->
                <div v-if="currentMethod === 'pem'" class="method-content">
                    <div class="alert alert-info" style="border-radius: 10px; border-left: 4px solid #0dcaf0;">
                        <strong>ℹ️ Информация</strong> Загрузите PEM файл с приватным ключом (secp256k1 для Ethereum).
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
                        
                <!-- Result -->
                <div v-if="result" class="seed-result-card">
                    <div class="seed-result-title">
                        <span>✅</span>
                        <span>Ключ успешно создан</span>
                    </div>
                    <div class="seed-result-item">
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
                    <div class="seed-result-item" v-if="result.keyType">
                        <label class="seed-result-label">Тип ключа:</label>
                        <div class="seed-result-value">[[ result.keyType ]]</div>
                    </div>
                    <div class="alert alert-warning mt-3" style="border-radius: 10px; border-left: 4px solid #ffc107;">
                        <strong>🔒 Безопасность</strong> Сохраните эту информацию в безопасном месте.
                    </div>
                </div>
            </template>
            <template #footer>
                <button class="modal-default-button btn btn-secondary" @click="closeModal">
                    Закрыть
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