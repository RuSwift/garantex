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
        
                        <div v-if="$slots.footer" ref="footer" class="modal-footer">
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

// Universal Confirmation Dialog Component
Vue.component('confirm-dialog', {
    delimiters: ['[[', ']]'],
    props: {
        show: {
            type: Boolean,
            default: false
        },
        title: {
            type: String,
            default: 'Подтверждение'
        },
        message: {
            type: String,
            required: true
        },
        confirmText: {
            type: String,
            default: 'Подтвердить'
        },
        cancelText: {
            type: String,
            default: 'Отмена'
        },
        type: {
            type: String,
            default: 'warning', // 'danger', 'warning', 'info', 'success'
            validator: (value) => ['danger', 'warning', 'info', 'success'].includes(value)
        },
        width: {
            type: String,
            default: '500px'
        },
        showCancel: {
            type: Boolean,
            default: true
        },
        loading: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        headerClass() {
            const classes = {
                'danger': 'bg-danger text-white',
                'warning': 'bg-warning text-dark',
                'info': 'bg-info text-white',
                'success': 'bg-success text-white'
            };
            return classes[this.type] || classes.warning;
        },
        confirmButtonClass() {
            const classes = {
                'danger': 'btn-danger',
                'warning': 'btn-warning',
                'info': 'btn-info',
                'success': 'btn-success'
            };
            return classes[this.type] || 'btn-warning';
        },
        icon() {
            const icons = {
                'danger': 'fas fa-exclamation-triangle',
                'warning': 'fas fa-exclamation-circle',
                'info': 'fas fa-info-circle',
                'success': 'fas fa-check-circle'
            };
            return icons[this.type] || icons.warning;
        }
    },
    methods: {
        handleConfirm() {
            this.$emit('confirm');
        },
        handleCancel() {
            this.$emit('cancel');
        },
        handleClose() {
            if (!this.loading) {
                this.$emit('cancel');
            }
        }
    },
    template: `
        <div v-if="show" class="modal fade show" style="display: block; background-color: rgba(0, 0, 0, 0.5);" tabindex="-1" @click.self="handleClose">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content" style="box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);">
                    <div class="modal-header" :class="headerClass">
                        <h5 class="modal-title">
                            <i :class="icon + ' me-2'"></i>
                            [[ title ]]
                        </h5>
                        <button type="button" class="btn-close" :class="type === 'danger' || type === 'info' || type === 'success' ? 'btn-close-white' : ''" @click="handleClose" :disabled="loading"></button>
                    </div>
                    <div class="modal-body" style="padding: 2rem;">
                        <p class="mb-0">[[ message ]]</p>
                    </div>
                    <div class="modal-footer">
                        <button 
                            type="button" 
                            class="btn btn-secondary" 
                            @click="handleCancel"
                            :disabled="loading"
                            v-if="showCancel">
                            [[ cancelText ]]
                        </button>
                        <button 
                            type="button" 
                            class="btn" 
                            :class="confirmButtonClass"
                            @click="handleConfirm"
                            :disabled="loading">
                            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                            [[ confirmText ]]
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
});

// Universal Form Dialog Component
Vue.component('form-dialog', {
    delimiters: ['[[', ']]'],
    props: {
        show: {
            type: Boolean,
            default: false
        },
        title: {
            type: String,
            required: true
        },
        fields: {
            type: Array,
            required: true,
            // Each field should have: { name, label, type, placeholder, required, value, options (for select), validation }
            validator: (fields) => {
                return fields.every(field => 
                    field.name && field.label && field.type
                );
            }
        },
        submitText: {
            type: String,
            default: 'Сохранить'
        },
        cancelText: {
            type: String,
            default: 'Отмена'
        },
        width: {
            type: String,
            default: '600px'
        },
        loading: {
            type: Boolean,
            default: false
        },
        errors: {
            type: Object,
            default: () => ({})
        }
    },
    data() {
        return {
            formData: {}
        };
    },
    watch: {
        show(newVal) {
            if (newVal) {
                this.initFormData();
            }
        },
        fields: {
            handler() {
                this.initFormData();
            },
            deep: true
        }
    },
    methods: {
        initFormData() {
            const data = {};
            this.fields.forEach(field => {
                data[field.name] = field.value !== undefined ? field.value : 
                    (field.type === 'checkbox' ? false : 
                     field.type === 'number' ? 0 : '');
            });
            this.formData = data;
        },
        handleSubmit() {
            // Validate form
            const validationErrors = {};
            this.fields.forEach(field => {
                if (field.required && !this.formData[field.name]) {
                    validationErrors[field.name] = `Поле "${field.label}" обязательно для заполнения`;
                } else if (field.validation) {
                    const error = field.validation(this.formData[field.name], this.formData);
                    if (error) {
                        validationErrors[field.name] = error;
                    }
                }
            });

            if (Object.keys(validationErrors).length > 0) {
                this.$emit('validation-error', validationErrors);
                return;
            }

            this.$emit('submit', { ...this.formData });
        },
        handleCancel() {
            this.$emit('cancel');
        },
        handleClose() {
            if (!this.loading) {
                this.$emit('cancel');
            }
        },
        getFieldError(fieldName) {
            return this.errors[fieldName] || '';
        },
        getFieldClass(field) {
            const baseClass = 'form-control';
            const error = this.getFieldError(field.name);
            return error ? `${baseClass} is-invalid` : baseClass;
        }
    },
    template: `
        <div v-if="show" class="modal fade show" style="display: block; background-color: rgba(0, 0, 0, 0.5);" tabindex="-1" @click.self="handleClose">
            <div class="modal-dialog modal-dialog-centered" :style="{ maxWidth: width }">
                <div class="modal-content" style="box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">[[ title ]]</h5>
                        <button type="button" class="btn-close btn-close-white" @click="handleClose" :disabled="loading"></button>
                    </div>
                    <div class="modal-body" style="padding: 2rem;">
                        <form @submit.prevent="handleSubmit">
                            <div v-for="field in fields" :key="field.name" class="mb-3">
                                <label :for="'field-' + field.name" class="form-label">
                                    [[ field.label ]]
                                    <span v-if="field.required" class="text-danger">*</span>
                                </label>
                                
                                <!-- Text, Email, Password, Number inputs -->
                                <input 
                                    v-if="['text', 'email', 'password', 'number', 'tel', 'url'].includes(field.type)"
                                    :type="field.type"
                                    :id="'field-' + field.name"
                                    :class="getFieldClass(field)"
                                    :placeholder="field.placeholder || ''"
                                    :required="field.required"
                                    :disabled="loading || field.disabled"
                                    :min="field.min"
                                    :max="field.max"
                                    :step="field.step"
                                    v-model="formData[field.name]"
                                />
                                
                                <!-- Textarea -->
                                <textarea 
                                    v-else-if="field.type === 'textarea'"
                                    :id="'field-' + field.name"
                                    :class="getFieldClass(field)"
                                    :placeholder="field.placeholder || ''"
                                    :required="field.required"
                                    :disabled="loading || field.disabled"
                                    :rows="field.rows || 3"
                                    v-model="formData[field.name]"
                                ></textarea>
                                
                                <!-- Select -->
                                <select 
                                    v-else-if="field.type === 'select'"
                                    :id="'field-' + field.name"
                                    :class="getFieldClass(field)"
                                    :required="field.required"
                                    :disabled="loading || field.disabled"
                                    v-model="formData[field.name]"
                                >
                                    <option value="" v-if="!field.required">-- Выберите --</option>
                                    <option 
                                        v-for="option in field.options" 
                                        :key="option.value" 
                                        :value="option.value"
                                    >
                                        [[ option.label || option.value ]]
                                    </option>
                                </select>
                                
                                <!-- Checkbox -->
                                <div v-else-if="field.type === 'checkbox'" class="form-check">
                                    <input 
                                        :id="'field-' + field.name"
                                        type="checkbox"
                                        class="form-check-input"
                                        :required="field.required"
                                        :disabled="loading || field.disabled"
                                        v-model="formData[field.name]"
                                    />
                                    <label :for="'field-' + field.name" class="form-check-label" v-if="field.checkboxLabel">
                                        [[ field.checkboxLabel ]]
                                    </label>
                                </div>
                                
                                <!-- Radio buttons -->
                                <div v-else-if="field.type === 'radio'" class="form-check" v-for="option in field.options" :key="option.value">
                                    <input 
                                        :id="'field-' + field.name + '-' + option.value"
                                        type="radio"
                                        :name="field.name"
                                        class="form-check-input"
                                        :value="option.value"
                                        :required="field.required"
                                        :disabled="loading || field.disabled"
                                        v-model="formData[field.name]"
                                    />
                                    <label :for="'field-' + field.name + '-' + option.value" class="form-check-label">
                                        [[ option.label || option.value ]]
                                    </label>
                                </div>
                                
                                <!-- Error message -->
                                <div v-if="getFieldError(field.name)" class="invalid-feedback d-block">
                                    [[ getFieldError(field.name) ]]
                                </div>
                                
                                <!-- Help text -->
                                <small v-if="field.help" class="form-text text-muted">
                                    [[ field.help ]]
                                </small>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button 
                            type="button" 
                            class="btn btn-secondary" 
                            @click="handleCancel"
                            :disabled="loading">
                            [[ cancelText ]]
                        </button>
                        <button 
                            type="button" 
                            class="btn btn-primary" 
                            @click="handleSubmit"
                            :disabled="loading">
                            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                            [[ submitText ]]
                        </button>
                    </div>
                </div>
            </div>
        </div>
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
            endpointStatus: { message: '', type: '', visible: false },
            // Direct GET request
            testingDirectGet: false,
            directGetResult: null
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
            this.directGetResult = null;
            this.hideEndpointStatus();
        },
        cancelEditingEndpoint() {
            this.editingEndpoint = false;
            this.serviceEndpoint = '';
            this.endpointVerified = false;
            this.endpointTestResult = null;
            this.directGetResult = null;
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
        async testDirectGetToCurrentEndpoint() {
            const endpoint = this.keyInfo?.service_endpoint;
            if (!endpoint) {
                return;
            }
            
            try {
                this.testingDirectGet = true;
                this.directGetResult = null;
                
                const startTime = performance.now();
                
                const response = await fetch(endpoint, {
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache',
                    headers: {
                        'Accept': 'application/json, text/plain, */*'
                    }
                });
                
                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);
                
                // Пытаемся прочитать тело ответа
                let responseBody = '';
                let responseData = null;
                const contentType = response.headers.get('content-type');
                
                try {
                    if (contentType && contentType.includes('application/json')) {
                        responseData = await response.json();
                        responseBody = JSON.stringify(responseData, null, 2);
                    } else {
                        responseBody = await response.text();
                    }
                } catch (e) {
                    responseBody = '[Не удалось прочитать тело ответа]';
                }
                
                this.directGetResult = {
                    success: response.ok,
                    status_code: response.status,
                    status_text: response.statusText,
                    response_time_ms: responseTime,
                    content_type: contentType,
                    body: responseBody,
                    headers: Object.fromEntries(response.headers.entries())
                };
                
            } catch (error) {
                console.error('Error with direct GET request:', error);
                this.directGetResult = {
                    success: false,
                    error: error.message,
                    error_type: error.name
                };
            } finally {
                this.testingDirectGet = false;
            }
        },
        async testDirectGetEndpoint() {
            if (!this.serviceEndpoint || !this.serviceEndpoint.trim()) {
                this.showEndpointStatus('Введите URL эндпоинта', 'error');
                return;
            }
            
            try {
                this.testingDirectGet = true;
                this.directGetResult = null;
                this.showEndpointStatus('Выполняется прямой GET запрос...', 'info');
                
                const startTime = performance.now();
                
                const response = await fetch(this.serviceEndpoint, {
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache',
                    headers: {
                        'Accept': 'application/json, text/plain, */*'
                    }
                });
                
                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);
                
                // Пытаемся прочитать тело ответа
                let responseBody = '';
                let responseData = null;
                const contentType = response.headers.get('content-type');
                
                try {
                    if (contentType && contentType.includes('application/json')) {
                        responseData = await response.json();
                        responseBody = JSON.stringify(responseData, null, 2);
                    } else {
                        responseBody = await response.text();
                    }
                } catch (e) {
                    responseBody = '[Не удалось прочитать тело ответа]';
                }
                
                this.directGetResult = {
                    success: response.ok,
                    status_code: response.status,
                    status_text: response.statusText,
                    response_time_ms: responseTime,
                    content_type: contentType,
                    body: responseBody,
                    headers: Object.fromEntries(response.headers.entries())
                };
                
                if (response.ok) {
                    this.showEndpointStatus(
                        `✅ GET запрос успешен (HTTP ${response.status}, ${responseTime}ms)`,
                        'success'
                    );
                } else {
                    this.showEndpointStatus(
                        `⚠️ GET запрос вернул HTTP ${response.status} ${response.statusText}`,
                        'error'
                    );
                }
                
            } catch (error) {
                console.error('Error with direct GET request:', error);
                this.directGetResult = {
                    success: false,
                    error: error.message,
                    error_type: error.name
                };
                this.showEndpointStatus('Ошибка: ' + error.message, 'error');
            } finally {
                this.testingDirectGet = false;
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
                        
                        <button 
                            v-if="keyInfo.service_endpoint"
                            class="btn btn-info mb-2" 
                            :disabled="testingDirectGet"
                            @click="testDirectGetToCurrentEndpoint">
                            [[ testingDirectGet ? '🔄 Выполняется...' : '🔗 Проверить GET запросом' ]]
                        </button>
                        
                        <div v-if="directGetResult && !editingEndpoint" class="card mb-3" style="border-radius: 10px;">
                            <div class="card-header" :class="directGetResult.success ? 'bg-success text-white' : 'bg-danger text-white'">
                                <strong>
                                    [[ directGetResult.success ? '✅ GET запрос успешен' : '❌ GET запрос завершился с ошибкой' ]]
                                </strong>
                            </div>
                            <div class="card-body">
                                <div v-if="directGetResult.error">
                                    <p class="mb-1"><strong>Ошибка:</strong> [[ directGetResult.error ]]</p>
                                    <p class="mb-0" v-if="directGetResult.error_type">
                                        <small><strong>Тип:</strong> [[ directGetResult.error_type ]]</small>
                                    </p>
                                </div>
                                <div v-else>
                                    <p class="mb-2">
                                        <strong>HTTP Status:</strong> 
                                        <span :class="directGetResult.status_code === 200 ? 'text-success' : 'text-warning'">
                                            [[ directGetResult.status_code ]] [[ directGetResult.status_text ]]
                                        </span>
                                    </p>
                                    <p class="mb-2">
                                        <strong>Время ответа:</strong> [[ directGetResult.response_time_ms ]] мс
                                    </p>
                                    <p class="mb-2" v-if="directGetResult.content_type">
                                        <strong>Content-Type:</strong> <code>[[ directGetResult.content_type ]]</code>
                                    </p>
                                    
                                    <div class="mb-2">
                                        <strong>Тело ответа:</strong>
                                        <pre class="bg-light p-2 mt-1" style="border-radius: 5px; max-height: 300px; overflow: auto; font-size: 0.85rem;">[[ directGetResult.body ]]</pre>
                                    </div>
                                    
                                    <details class="mt-2">
                                        <summary style="cursor: pointer;"><strong>Заголовки ответа</strong></summary>
                                        <pre class="bg-light p-2 mt-1" style="border-radius: 5px; max-height: 200px; overflow: auto; font-size: 0.85rem;">[[ JSON.stringify(directGetResult.headers, null, 2) ]]</pre>
                                    </details>
                                </div>
                            </div>
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
                                @input="endpointVerified = false; endpointTestResult = null; directGetResult = null"
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
                        
                        <button 
                            class="btn btn-info me-2 mb-2" 
                            :disabled="!serviceEndpoint || testingDirectGet"
                            @click="testDirectGetEndpoint">
                            [[ testingDirectGet ? '🔄 Выполняется...' : '🔗 Прямой GET запрос' ]]
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
                        
                        <div v-if="directGetResult" class="card mb-3" style="border-radius: 10px;">
                            <div class="card-header" :class="directGetResult.success ? 'bg-success text-white' : 'bg-danger text-white'">
                                <strong>
                                    [[ directGetResult.success ? '✅ GET запрос успешен' : '❌ GET запрос завершился с ошибкой' ]]
                                </strong>
                            </div>
                            <div class="card-body">
                                <div v-if="directGetResult.error">
                                    <p class="mb-1"><strong>Ошибка:</strong> [[ directGetResult.error ]]</p>
                                    <p class="mb-0" v-if="directGetResult.error_type">
                                        <small><strong>Тип:</strong> [[ directGetResult.error_type ]]</small>
                                    </p>
                                </div>
                                <div v-else>
                                    <p class="mb-2">
                                        <strong>HTTP Status:</strong> 
                                        <span :class="directGetResult.status_code === 200 ? 'text-success' : 'text-warning'">
                                            [[ directGetResult.status_code ]] [[ directGetResult.status_text ]]
                                        </span>
                                    </p>
                                    <p class="mb-2">
                                        <strong>Время ответа:</strong> [[ directGetResult.response_time_ms ]] мс
                                    </p>
                                    <p class="mb-2" v-if="directGetResult.content_type">
                                        <strong>Content-Type:</strong> <code>[[ directGetResult.content_type ]]</code>
                                    </p>
                                    
                                    <div class="mb-2">
                                        <strong>Тело ответа:</strong>
                                        <pre class="bg-light p-2 mt-1" style="border-radius: 5px; max-height: 300px; overflow: auto; font-size: 0.85rem;">[[ directGetResult.body ]]</pre>
                                    </div>
                                    
                                    <details class="mt-2">
                                        <summary style="cursor: pointer;"><strong>Заголовки ответа</strong></summary>
                                        <pre class="bg-light p-2 mt-1" style="border-radius: 5px; max-height: 200px; overflow: auto; font-size: 0.85rem;">[[ JSON.stringify(directGetResult.headers, null, 2) ]]</pre>
                                    </details>
                                </div>
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

// Wallets Component
Vue.component('Wallets', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            activeTab: 'wallets', // 'wallets' or 'managers'
            
            // Wallets data
            loading: true,
            wallets: [],
            total: 0,
            
            // Create wallet modal
            showCreateModal: false,
            walletForm: {
                name: '',
                mnemonic: ''
            },
            savingWallet: false,
            
            // Edit wallet name
            editingWalletId: null,
            editingWalletName: '',
            savingName: false,
            
            // Delete confirmation
            walletToDelete: null,
            
            // Managers data
            loadingManagers: true,
            managers: [],
            managersTotal: 0,
            managersPage: 1,
            managersPageSize: 20,
            
            // Create/Edit manager modal
            showManagerModal: false,
            editingManager: null,
            managerForm: {
                wallet_address: '',
                blockchain: 'tron',
                nickname: '',
                is_verified: false,
                access_to_admin_panel: true
            },
            savingManager: false,
            
            // Delete manager confirmation
            managerToDelete: null,
            
            // Permissions modal
            showPermissionsModal: false,
            permissionsWallet: null,
            loadingPermissions: false,
            permissionsData: null,
            addressUsernames: {}, // Cache for address -> username mapping
            tronNetwork: 'mainnet', // TRON network (mainnet, shasta, nile)
            
            // Update permissions wizard
            showUpdatePermissionsModal: false,
            updatePermissionsWallet: null,
            availableManagers: [], // Managers for address selection
            loadingManagers: false,
            updatePermissionsForm: {
                threshold: 2,
                permission_name: 'multisig',
                keys: [], // Array of {address: '', weight: 1}
                operations: '7fff1fc0033e0000000000000000000000000000000000000000000000000000' // Canonical operations mask
            },
            creatingUpdateTx: false,
            updateTxResult: null,
            updateTxUnsignedTransaction: null, // Полная транзакция для подписи
            updateTxSigning: false, // Состояние подписи
            updateTxBroadcasting: false, // Состояние broadcast
            updateTxFinalResult: null, // Результат broadcast
            
            // DIDDoc modal
            showDidDocModalFlag: false,
            didDocUserId: null,
            didDocOwnerInfo: null,
            
            statusMessage: '',
            statusType: ''
        };
    },
    mounted() {
        this.loadWallets();
        this.loadTronNetwork();
    },
    methods: {
        async loadWallets() {
            this.loading = true;
            try {
                const response = await fetch('/api/wallets', {
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    let errorMessage = 'Ошибка загрузки кошельков';
                    
                    if (response.status === 401) {
                        errorMessage = 'Требуется авторизация администратора';
                    } else if (response.status === 403) {
                        errorMessage = 'Доступ запрещен';
                    } else {
                        // Попытаемся получить детали ошибки из ответа
                        try {
                            const errorData = await response.json();
                            errorMessage = errorData.detail || errorMessage;
                        } catch (e) {
                            errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                        }
                    }
                    
                    throw new Error(errorMessage);
                }
                
                const data = await response.json();
                this.wallets = data.wallets || [];
                this.total = data.total || 0;
                
            } catch (error) {
                console.error('Error loading wallets:', error);
                this.showStatus('Ошибка загрузки кошельков: ' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },
        
        showCreateWalletModal() {
            this.walletForm = {
                name: '',
                mnemonic: ''
            };
            this.showCreateModal = true;
        },
        
        closeCreateModal() {
            this.showCreateModal = false;
            this.walletForm = {
                name: '',
                mnemonic: ''
            };
        },
        
        validateMnemonic(mnemonic) {
            // Базовая валидация: проверяем, что это строка и содержит слова
            if (!mnemonic || typeof mnemonic !== 'string') {
                return false;
            }
            
            const words = mnemonic.trim().split(/\s+/);
            // Мнемоника обычно содержит 12, 15, 18, 21 или 24 слова
            return words.length >= 12 && words.length <= 24;
        },
        
        async createWallet() {
            if (!this.walletForm.name || !this.walletForm.name.trim()) {
                this.showStatus('Введите имя кошелька', 'error');
                return;
            }
            
            if (!this.walletForm.mnemonic || !this.walletForm.mnemonic.trim()) {
                this.showStatus('Введите мнемоническую фразу', 'error');
                return;
            }
            
            if (!this.validateMnemonic(this.walletForm.mnemonic)) {
                this.showStatus('Мнемоническая фраза должна содержать от 12 до 24 слов', 'error');
                return;
            }
            
            this.savingWallet = true;
            
            try {
                const response = await fetch('/api/wallets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        name: this.walletForm.name.trim(),
                        mnemonic: this.walletForm.mnemonic.trim()
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка создания кошелька');
                }
                
                this.showStatus('Кошелек успешно создан', 'success');
                this.closeCreateModal();
                await this.loadWallets();
                
            } catch (error) {
                console.error('Error creating wallet:', error);
                this.showStatus('Ошибка создания кошелька: ' + error.message, 'error');
            } finally {
                this.savingWallet = false;
            }
        },
        
        startEditingName(wallet) {
            this.editingWalletId = wallet.id;
            this.editingWalletName = wallet.name;
        },
        
        cancelEditingName() {
            this.editingWalletId = null;
            this.editingWalletName = '';
        },
        
        async saveWalletName(wallet) {
            if (!this.editingWalletName || !this.editingWalletName.trim()) {
                this.showStatus('Имя не может быть пустым', 'error');
                return;
            }
            
            this.savingName = true;
            
            try {
                const response = await fetch(`/api/wallets/${wallet.id}/name`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        name: this.editingWalletName.trim()
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка обновления имени');
                }
                
                this.showStatus('Имя кошелька обновлено', 'success');
                this.cancelEditingName();
                await this.loadWallets();
                
            } catch (error) {
                console.error('Error updating wallet name:', error);
                this.showStatus('Ошибка обновления имени: ' + error.message, 'error');
            } finally {
                this.savingName = false;
            }
        },
        
        confirmDelete(wallet) {
            this.walletToDelete = wallet;
        },
        
        cancelDelete() {
            this.walletToDelete = null;
        },
        
        async deleteWallet() {
            if (!this.walletToDelete) return;
            
            try {
                const response = await fetch(`/api/wallets/${this.walletToDelete.id}`, {
                    method: 'DELETE',
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка удаления кошелька');
                }
                
                this.showStatus('Кошелек успешно удален', 'success');
                this.cancelDelete();
                await this.loadWallets();
                
            } catch (error) {
                console.error('Error deleting wallet:', error);
                this.showStatus('Ошибка удаления кошелька: ' + error.message, 'error');
            }
        },
        
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.showStatus('Адрес скопирован в буфер обмена', 'success');
            }).catch(err => {
                console.error('Error copying to clipboard:', err);
                this.showStatus('Ошибка копирования', 'error');
            });
        },
        
        getTronScanUrl(txId) {
            if (!txId) return '#';
            return `https://tronscan.org/#/transaction/${txId}`;
        },
        
        formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleString('ru-RU');
        },
        
        showStatus(message, type) {
            this.statusMessage = message;
            this.statusType = type;
            setTimeout(() => {
                this.statusMessage = '';
                this.statusType = '';
            }, 5000);
        },
        
        // Tab switching
        switchTab(tab) {
            this.activeTab = tab;
            if (tab === 'managers' && this.managers.length === 0) {
                this.loadManagers();
            }
        },
        
        // Managers methods
        async loadManagers() {
            this.loadingManagers = true;
            try {
                const params = new URLSearchParams({
                    page: this.managersPage,
                    page_size: this.managersPageSize,
                    access_to_admin_panel: 'true'
                });
                
                const url = '/api/admin/wallet-users?' + params.toString();
                console.log('Loading managers from:', url);
                
                const response = await fetch(url, {
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Failed to load managers:', errorText);
                    throw new Error('Failed to load managers');
                }
                
                const data = await response.json();
                console.log('Managers loaded:', data.users?.length || 0, 'of', data.total || 0);
                this.managers = data.users || [];
                this.managersTotal = data.total || 0;
                
            } catch (error) {
                console.error('Error loading managers:', error);
                this.showStatus('Ошибка загрузки менеджеров: ' + error.message, 'error');
            } finally {
                this.loadingManagers = false;
            }
        },
        
        showCreateManagerModal() {
            this.editingManager = null;
            this.managerForm = {
                wallet_address: '',
                blockchain: 'tron',
                nickname: '',
                is_verified: false,
                access_to_admin_panel: true
            };
            this.showManagerModal = true;
        },
        
        showEditManagerModal(manager) {
            this.editingManager = manager;
            this.managerForm = {
                wallet_address: manager.wallet_address,
                blockchain: manager.blockchain,
                nickname: manager.nickname,
                is_verified: manager.is_verified || false,
                access_to_admin_panel: manager.access_to_admin_panel || false
            };
            this.showManagerModal = true;
        },
        
        closeManagerModal() {
            this.showManagerModal = false;
            this.editingManager = null;
            this.managerForm = {
                wallet_address: '',
                blockchain: 'tron',
                nickname: '',
                is_verified: false,
                access_to_admin_panel: true
            };
        },
        
        async saveManager() {
            if (!this.managerForm.wallet_address || !this.managerForm.blockchain || !this.managerForm.nickname) {
                this.showStatus('Заполните все поля', 'error');
                return;
            }
            
            // Валидация адреса кошелька (только при создании нового менеджера)
            if (!this.editingManager) {
                if (!this.validateWalletAddress(this.managerForm.wallet_address, this.managerForm.blockchain)) {
                    const blockchainName = this.managerForm.blockchain === 'tron' ? 'TRON' : 'Ethereum';
                    const expectedFormat = this.managerForm.blockchain === 'tron' 
                        ? '34 символа, начинается с T (например: TRCW29HRORXWcw3PoEEaQzZaRLiZjbkFnS)'
                        : '42 символа, начинается с 0x (например: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb)';
                    this.showStatus(`Неверный формат адреса ${blockchainName}. Ожидается: ${expectedFormat}`, 'error');
                    return;
                }
            }
            
            this.savingManager = true;
            
            try {
                // Если редактируем существующего менеджера
                if (this.editingManager) {
                    const url = '/api/admin/wallet-users/' + this.editingManager.id;
                    const body = {
                        nickname: this.managerForm.nickname,
                        blockchain: this.managerForm.blockchain,
                        is_verified: this.managerForm.is_verified,
                        access_to_admin_panel: this.managerForm.access_to_admin_panel
                    };
                    
                    const response = await fetch(url, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include',
                        body: JSON.stringify(body)
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to update manager');
                    }
                    
                    this.showStatus('Менеджер обновлен', 'success');
                    this.closeManagerModal();
                    await this.loadManagers();
                    return;
                }
                
                // Если создаем нового менеджера - сначала пытаемся создать
                let response = await fetch('/api/admin/wallet-users', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify(this.managerForm)
                });
                
                // Если пользователь уже существует, обновляем его access_to_admin_panel
                if (!response.ok) {
                    const errorData = await response.json();
                    const errorMessage = errorData.detail || '';
                    
                    // Проверяем, что это ошибка "already exists"
                    if (response.status === 400 && errorMessage.includes('already exists')) {
                        // Ищем пользователя по wallet_address
                        const searchResponse = await fetch(
                            `/api/admin/wallet-users?query=${encodeURIComponent(this.managerForm.wallet_address)}&page_size=1`,
                            {
                                method: 'GET',
                                credentials: 'include'
                            }
                        );
                        
                        if (!searchResponse.ok) {
                            throw new Error('Failed to find existing user');
                        }
                        
                        const searchData = await searchResponse.json();
                        const existingUser = searchData.users && searchData.users.length > 0 
                            ? searchData.users.find(u => u.wallet_address === this.managerForm.wallet_address)
                            : null;
                        
                        if (!existingUser) {
                            throw new Error('User exists but could not be found');
                        }
                        
                        // Обновляем пользователя: устанавливаем access_to_admin_panel = True
                        const updateResponse = await fetch('/api/admin/wallet-users/' + existingUser.id, {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            credentials: 'include',
                            body: JSON.stringify({
                                nickname: this.managerForm.nickname,
                                blockchain: this.managerForm.blockchain,
                                is_verified: existingUser.is_verified || this.managerForm.is_verified,
                                access_to_admin_panel: true  // Устанавливаем флаг менеджера
                            })
                        });
                        
                        if (!updateResponse.ok) {
                            const updateError = await updateResponse.json();
                            throw new Error(updateError.detail || 'Failed to update existing user');
                        }
                        
                        this.showStatus('Пользователь найден. Права менеджера активированы', 'success');
                        this.closeManagerModal();
                        await this.loadManagers();
                        return;
                    } else {
                        // Другая ошибка
                        throw new Error(errorMessage || 'Failed to save manager');
                    }
                }
                
                // Успешное создание нового пользователя
                this.showStatus('Менеджер создан', 'success');
                this.closeManagerModal();
                await this.loadManagers();
                
            } catch (error) {
                console.error('Error saving manager:', error);
                this.showStatus('Ошибка сохранения: ' + error.message, 'error');
            } finally {
                this.savingManager = false;
            }
        },
        
        confirmDeleteManager(manager) {
            this.managerToDelete = manager;
        },
        
        cancelDeleteManager() {
            this.managerToDelete = null;
        },
        
        async deleteManager() {
            if (!this.managerToDelete) return;
            
            try {
                // Вместо удаления, устанавливаем access_to_admin_panel = False
                const response = await fetch('/api/admin/wallet-users/' + this.managerToDelete.id, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        nickname: this.managerToDelete.nickname,
                        blockchain: this.managerToDelete.blockchain,
                        is_verified: this.managerToDelete.is_verified,
                        access_to_admin_panel: false  // Отключаем права менеджера
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to remove manager access');
                }
                
                this.showStatus('Права менеджера отключены. Пользователь сохранен в системе', 'success');
                this.managerToDelete = null;
                await this.loadManagers();
                
            } catch (error) {
                console.error('Error removing manager access:', error);
                this.showStatus('Ошибка: ' + error.message, 'error');
            }
        },
        
        truncateAddress(address) {
            if (!address || address.length <= 16) return address;
            return address.substring(0, 8) + '...' + address.substring(address.length - 6);
        },
        
        validateWalletAddress(address, blockchain) {
            if (!address || typeof address !== 'string') {
                return false;
            }
            
            const trimmedAddress = address.trim();
            
            if (blockchain === 'tron') {
                // TRON адреса начинаются с 'T', длина 34 символа
                if (trimmedAddress.length !== 34) {
                    return false;
                }
                if (!trimmedAddress.startsWith('T')) {
                    return false;
                }
                // Проверка на Base58 символы (1-9, A-H, J-N, P-Z, a-k, m-z)
                const base58Regex = /^[1-9A-HJ-NP-Za-km-z]+$/;
                return base58Regex.test(trimmedAddress);
            } else if (blockchain === 'ethereum') {
                // Ethereum адреса начинаются с '0x', длина 42 символа
                if (trimmedAddress.length !== 42) {
                    return false;
                }
                if (!trimmedAddress.startsWith('0x') && !trimmedAddress.startsWith('0X')) {
                    return false;
                }
                // Проверка на hex символы (0-9, a-f, A-F)
                const hexRegex = /^0x[0-9a-fA-F]{40}$/;
                return hexRegex.test(trimmedAddress);
            }
            
            return false;
        },
        
        // Permissions methods
        async fetchWalletPermissions(wallet) {
            this.loadingPermissions = true;
            this.permissionsWallet = wallet;
            this.permissionsData = null;
            
            try {
                const response = await fetch(`/api/wallets/${wallet.id}/fetch-permissions`, {
                    method: 'POST',
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка получения permissions');
                }
                
                const data = await response.json();
                this.permissionsData = data.account_permissions;
                
                // Load usernames for all addresses in permissions
                await this.loadUsernamesForPermissions(data.account_permissions);
                
                // Update wallet in list
                const walletIndex = this.wallets.findIndex(w => w.id === wallet.id);
                if (walletIndex !== -1) {
                    this.wallets[walletIndex].account_permissions = data.account_permissions;
                }
                
                this.showPermissionsModal = true;
                
            } catch (error) {
                console.error('Error fetching permissions:', error);
                this.showStatus('Ошибка получения permissions: ' + error.message, 'error');
            } finally {
                this.loadingPermissions = false;
            }
        },
        
        async loadUsernamesForPermissions(permissions) {
            if (!permissions) return;
            
            const addresses = new Set();
            
            // Collect all addresses from permissions
            if (permissions.owner && permissions.owner.keys) {
                permissions.owner.keys.forEach(key => {
                    if (key.address) addresses.add(key.address);
                });
            }
            
            if (permissions.active && Array.isArray(permissions.active)) {
                permissions.active.forEach(perm => {
                    if (perm.keys) {
                        perm.keys.forEach(key => {
                            if (key.address) addresses.add(key.address);
                        });
                    }
                });
            }
            
            // Fetch usernames for all addresses
            for (const address of addresses) {
                if (!this.addressUsernames[address]) {
                    try {
                        const response = await fetch(`/api/wallets/addresses/${address}/username`, {
                            credentials: 'include'
                        });
                        if (response.ok) {
                            const data = await response.json();
                            if (data.found) {
                                this.addressUsernames[address] = data.username;
                            }
                        }
                    } catch (error) {
                        console.error(`Error loading username for ${address}:`, error);
                    }
                }
            }
        },
        
        getAddressDisplay(address) {
            if (!address) return '';
            const username = this.addressUsernames[address];
            if (username) {
                return `${username} (${address})`;
            }
            return address;
        },
        
        getOperationNames(operationsHex) {
            if (!operationsHex) return [];
            
            // TRON operation types mapping
            const operationMap = {
                'TransferContract': 'Перевод TRX',
                'TransferAssetContract': 'Перевод токенов',
                'TriggerSmartContract': 'Вызов смарт-контракта',
                'FreezeBalanceContract': 'Заморозка баланса',
                'UnfreezeBalanceContract': 'Разморозка баланса',
                'VoteWitnessContract': 'Голосование за свидетелей',
                'AccountPermissionUpdateContract': 'Обновление permissions',
                'CreateSmartContract': 'Создание смарт-контракта',
                'ProposalCreateContract': 'Создание предложения',
                'ProposalApproveContract': 'Одобрение предложения',
                'ProposalDeleteContract': 'Удаление предложения',
                'ExchangeCreateContract': 'Создание биржи',
                'ExchangeInjectContract': 'Пополнение биржи',
                'ExchangeWithdrawContract': 'Вывод с биржи',
                'ExchangeTransactionContract': 'Транзакция на бирже',
                'UpdateEnergyLimitContract': 'Обновление лимита энергии',
                'AccountCreateContract': 'Создание аккаунта',
                'WitnessCreateContract': 'Создание свидетеля',
                'WitnessUpdateContract': 'Обновление свидетеля',
                'AssetIssueContract': 'Выпуск токена',
                'ParticipateAssetIssueContract': 'Участие в выпуске токена',
                'UpdateAssetContract': 'Обновление токена',
                'UpdateSettingContract': 'Обновление настроек',
                'UpdateBrokerageContract': 'Обновление комиссии',
                'ClearABIContract': 'Очистка ABI',
                'UpdateAccountContract': 'Обновление аккаунта',
                'ShieldedTransferContract': 'Shielded транзакция',
                'MarketSellAssetContract': 'Продажа на рынке',
                'MarketCancelOrderContract': 'Отмена ордера',
                'WithdrawBalanceContract': 'Вывод баланса',
                'UnfreezeAssetContract': 'Разморозка токенов',
                'UpdateAccountPermissionContract': 'Обновление permissions аккаунта',
                'SetAccountIdContract': 'Установка ID аккаунта',
                'AccountPermissionUpdateContract': 'Обновление permissions',
                'CreateSmartContract': 'Создание смарт-контракта',
                'TriggerSmartContract': 'Вызов смарт-контракта',
                'UpdateBrokerageContract': 'Обновление комиссии',
                'ClearABIContract': 'Очистка ABI',
                'UpdateEnergyLimitContract': 'Обновление лимита энергии',
                'ShieldedTransferContract': 'Shielded транзакция',
                'MarketSellAssetContract': 'Продажа на рынке',
                'MarketCancelOrderContract': 'Отмена ордера',
                'WithdrawBalanceContract': 'Вывод баланса',
                'UnfreezeAssetContract': 'Разморозка токенов',
                'UpdateAccountPermissionContract': 'Обновление permissions аккаунта',
                'SetAccountIdContract': 'Установка ID аккаунта'
            };
            
            // Parse operations hex string
            // Operations are represented as a hex string where each bit represents an operation type
            // For simplicity, we'll return a generic message
            if (operationsHex === '7fff1fc0033e0000000000000000000000000000000000000000000000000000') {
                return ['Все операции разрешены'];
            }
            
            // Try to decode operations
            const operations = [];
            try {
                // Convert hex to binary and check each bit
                const binary = parseInt(operationsHex.substring(0, 16), 16).toString(2);
                // This is a simplified version - actual decoding is more complex
                operations.push('Операции настроены (детали в hex)');
            } catch (e) {
                operations.push('Операции: ' + operationsHex.substring(0, 32) + '...');
            }
            
            return operations;
        },
        
        closePermissionsModal() {
            this.showPermissionsModal = false;
            this.permissionsWallet = null;
            this.permissionsData = null;
        },
        
        async loadTronNetwork() {
            try {
                const response = await fetch('/api/wallets/tron-network', {
                    credentials: 'include'
                });
                if (response.ok) {
                    const data = await response.json();
                    this.tronNetwork = data.network || 'mainnet';
                }
            } catch (error) {
                console.error('Error loading TRON network:', error);
                // Default to mainnet
                this.tronNetwork = 'mainnet';
            }
        },
        
        getTronscanUrl(address) {
            if (!address) return '#';
            
            const baseUrls = {
                'mainnet': 'https://tronscan.org',
                'shasta': 'https://shasta.tronscan.org',
                'nile': 'https://nile.tronscan.org'
            };
            
            const baseUrl = baseUrls[this.tronNetwork] || baseUrls['mainnet'];
            return `${baseUrl}/#/address/${address}/permissions`;
        },
        
        // Update permissions wizard methods
        async showUpdatePermissionsWizard(wallet) {
            this.updatePermissionsWallet = wallet;
            
            // Initialize form with Owner address as first key
            const ownerKey = {
                address: wallet.tron_address,
                weight: 1,
                isOwner: true // Mark as owner key
            };
            
            this.updatePermissionsForm = {
                threshold: 2,
                permission_name: 'multisig',
                keys: [ownerKey], // Owner всегда первый
                operations: '7fff1fc0033e0000000000000000000000000000000000000000000000000000'
            };
            this.updateTxResult = null;
            this.showUpdatePermissionsModal = true;
            await this.loadAvailableManagers();
        },
        
        async loadAvailableManagers() {
            this.loadingManagers = true;
            try {
                const params = new URLSearchParams({
                    page: 1,
                    page_size: 100,
                    access_to_admin_panel: 'true'
                });
                
                const response = await fetch('/api/admin/wallet-users?' + params, {
                    credentials: 'include'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const managers = data.users || [];
                    
                    // Add Owner address at the beginning of the list
                    if (this.updatePermissionsWallet && this.updatePermissionsWallet.tron_address) {
                        const ownerEntry = {
                            id: 'owner',
                            wallet_address: this.updatePermissionsWallet.tron_address,
                            nickname: `Owner (${this.updatePermissionsWallet.name})`,
                            is_owner: true
                        };
                        this.availableManagers = [ownerEntry, ...managers];
                    } else {
                        this.availableManagers = managers;
                    }
                }
            } catch (error) {
                console.error('Error loading managers:', error);
            } finally {
                this.loadingManagers = false;
            }
        },
        
        addPermissionKey() {
            this.updatePermissionsForm.keys.push({
                address: '',
                weight: 1
            });
        },
        
        removePermissionKey(index) {
            // Нельзя удалить Owner ключ (первый ключ)
            if (this.updatePermissionsForm.keys[index] && this.updatePermissionsForm.keys[index].isOwner) {
                this.showStatus('Нельзя удалить ключ владельца (Owner)', 'error');
                return;
            }
            this.updatePermissionsForm.keys.splice(index, 1);
        },
        
        getTotalWeight() {
            return this.updatePermissionsForm.keys.reduce((sum, key) => {
                return sum + (parseInt(key.weight) || 0);
            }, 0);
        },
        
        isWeightValid() {
            const total = this.getTotalWeight();
            return total >= this.updatePermissionsForm.threshold;
        },
        
        getWeightValidationMessage() {
            const total = this.getTotalWeight();
            const threshold = this.updatePermissionsForm.threshold;
            if (total < threshold) {
                return `⚠️ ОПАСНО! Сумма весов (${total}) меньше threshold (${threshold}). Это заблокирует кошелек!`;
            }
            return `✓ Сумма весов (${total}) >= threshold (${threshold})`;
        },
        
        async createUpdatePermissionsTransaction() {
            // Validation
            if (!this.updatePermissionsForm.keys.length) {
                this.showStatus('Добавьте хотя бы один ключ', 'error');
                return;
            }
            
            if (!this.isWeightValid()) {
                this.showStatus('Сумма весов должна быть >= threshold', 'error');
                return;
            }
            
            // Validate all keys have addresses
            for (const key of this.updatePermissionsForm.keys) {
                if (!key.address || !key.address.trim()) {
                    this.showStatus('Все ключи должны иметь адрес', 'error');
                    return;
                }
                if (!this.validateWalletAddress(key.address, 'tron')) {
                    this.showStatus(`Неверный формат TRON адреса: ${key.address}`, 'error');
                    return;
                }
            }
            
            // Проверка: Owner должен быть в списке
            const hasOwner = this.updatePermissionsForm.keys.some(key => 
                key.isOwner && key.address === this.updatePermissionsWallet.tron_address
            );
            if (!hasOwner) {
                this.showStatus('Ключ владельца (Owner) должен присутствовать в списке', 'error');
                return;
            }
            
            this.creatingUpdateTx = true;
            this.updateTxResult = null;
            this.updateTxUnsignedTransaction = null;
            this.updateTxFinalResult = null;
            
            try {
                const response = await fetch(`/api/wallets/${this.updatePermissionsWallet.id}/update-permissions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        threshold: this.updatePermissionsForm.threshold,
                        permission_name: this.updatePermissionsForm.permission_name,
                        keys: this.updatePermissionsForm.keys.map(k => ({
                            address: k.address.trim(),
                            weight: parseInt(k.weight)
                        })), // isOwner не отправляется на сервер, только для UI
                        operations: this.updatePermissionsForm.operations
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка создания транзакции');
                }
                
                const data = await response.json();
                this.updateTxResult = data;
                this.updateTxUnsignedTransaction = data.unsigned_transaction || null;
                this.updateTxFinalResult = null;
                this.showStatus('Транзакция обновления permissions создана', 'success');
                
            } catch (error) {
                console.error('Error creating update transaction:', error);
                this.showStatus('Ошибка создания транзакции: ' + error.message, 'error');
            } finally {
                this.creatingUpdateTx = false;
            }
        },
        
        // Обработчики событий от TronSign компонента для updatePermissions
        async onUpdatePermissionsSigning(data) {
            this.updateTxSigning = true;
            this.showStatus('Подписание транзакции updatePermissions через TronLink...', 'info');
        },
        
        async onUpdatePermissionsSigned(data) {
            this.updateTxSigning = false;
            this.showStatus('Транзакция подписана. Отправка в блокчейн...', 'info');
            
            // Broadcast транзакции
            try {
                this.updateTxBroadcasting = true;
                
                const broadcastResponse = await fetch('/api/wallets/broadcast-usdt-transaction', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        signed_transaction: data.signedTransaction
                    })
                });
                
                if (!broadcastResponse.ok) {
                    let errorMessage = 'Ошибка отправки транзакции';
                    try {
                        const errorData = await broadcastResponse.json();
                        errorMessage = errorData.detail || errorData.message || errorMessage;
                    } catch (parseError) {
                        errorMessage = `Ошибка ${broadcastResponse.status}: ${broadcastResponse.statusText || 'Ошибка отправки транзакции'}`;
                    }
                    throw new Error(errorMessage);
                }
                
                const broadcastData = await broadcastResponse.json();
                
                if (broadcastData.success && broadcastData.result) {
                    this.updateTxFinalResult = {
                        success: true,
                        txId: broadcastData.txid || data.txId,
                        message: 'Транзакция updatePermissions успешно отправлена!'
                    };
                    this.showStatus('Транзакция updatePermissions успешно отправлена!', 'success');
                    
                    // Обновить список кошельков через 2 секунды
                    setTimeout(() => {
                        this.loadWallets();
                    }, 2000);
                } else {
                    throw new Error(broadcastData.message || 'Ошибка отправки транзакции');
                }
            } catch (error) {
                const errorMessage = error.message || 'Ошибка отправки транзакции';
                this.updateTxFinalResult = {
                    success: false,
                    message: errorMessage
                };
                this.showStatus('Ошибка: ' + errorMessage, 'error');
            } finally {
                this.updateTxBroadcasting = false;
            }
        },
        
        onUpdatePermissionsError(data) {
            this.updateTxSigning = false;
            this.updateTxBroadcasting = false;
            
            const errorMessage = data.message || 'Произошла ошибка';
            this.updateTxFinalResult = {
                success: false,
                message: errorMessage
            };
            
            this.showStatus('Ошибка: ' + errorMessage, 'error');
        },
        
        // Метод для вызова подписи транзакции через TronSign
        async signUpdatePermissionsTransaction() {
            if (!this.updateTxUnsignedTransaction) {
                this.showStatus('Транзакция не создана. Сначала создайте транзакцию', 'error');
                return;
            }
            
            try {
                await this.$refs.updatePermissionsTronSign.signTransaction(this.updateTxUnsignedTransaction);
            } catch (error) {
                // Ошибка уже обработана через событие error
                console.error('Error signing update permissions transaction:', error);
            }
        },
        
        closeUpdatePermissionsModal() {
            this.showUpdatePermissionsModal = false;
            this.updatePermissionsWallet = null;
            this.updatePermissionsForm = {
                threshold: 2,
                permission_name: 'multisig',
                keys: [],
                operations: '7fff1fc0033e0000000000000000000000000000000000000000000000000000'
            };
            this.updateTxResult = null;
            this.updateTxUnsignedTransaction = null;
            this.updateTxSigning = false;
            this.updateTxBroadcasting = false;
            this.updateTxFinalResult = null;
        },
        
        getTronScanUrl(txId) {
            if (!txId) return '#';
            return `https://tronscan.org/#/transaction/${txId}`;
        },
        
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.showStatus('Скопировано в буфер обмена', 'success');
            }).catch(err => {
                console.error('Copy error:', err);
                this.showStatus('Ошибка копирования', 'error');
            });
        },
        
        async showDidDocModalForWallet(wallet) {
            // Try to find user by wallet address (tron_address or ethereum_address)
            try {
                // First try TRON address
                let searchAddress = wallet.tron_address;
                let response = await fetch(`/api/admin/wallet-users?query=${encodeURIComponent(searchAddress)}`, {
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    throw new Error('Failed to search for user');
                }
                
                let data = await response.json();
                let user = null;
                
                // Find exact match
                if (data.users && data.users.length > 0) {
                    user = data.users.find(u => 
                        u.wallet_address.toLowerCase() === searchAddress.toLowerCase()
                    );
                }
                
                // If not found, try Ethereum address
                if (!user && wallet.ethereum_address) {
                    searchAddress = wallet.ethereum_address;
                    response = await fetch(`/api/admin/wallet-users?query=${encodeURIComponent(searchAddress)}`, {
                        credentials: 'include'
                    });
                    
                    if (response.ok) {
                        data = await response.json();
                        if (data.users && data.users.length > 0) {
                            user = data.users.find(u => 
                                u.wallet_address.toLowerCase() === searchAddress.toLowerCase()
                            );
                        }
                    }
                }
                
                if (user) {
                    this.didDocUserId = user.id;
                    this.didDocOwnerInfo = {
                        nickname: user.nickname,
                        avatar: user.avatar
                    };
                    this.showDidDocModalFlag = true;
                } else {
                    this.showStatus('Пользователь с таким адресом кошелька не найден', 'error');
                }
            } catch (error) {
                console.error('Error finding user for wallet:', error);
                this.showStatus('Ошибка поиска пользователя: ' + error.message, 'error');
            }
        },
        
        closeDidDocModal() {
            this.showDidDocModalFlag = false;
            this.didDocUserId = null;
            this.didDocOwnerInfo = null;
        }
    },
    template: `
        <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <i class="fas fa-wallet me-1"></i>
                    Управление кошельками и менеджерами
                </div>
                <div>
                    <button v-if="activeTab === 'wallets'" class="btn btn-primary btn-sm" @click="showCreateWalletModal">
                        <i class="fas fa-plus me-1"></i>
                        Добавить кошелек
                    </button>
                    <button v-else class="btn btn-primary btn-sm" @click="showCreateManagerModal">
                        <i class="fas fa-plus me-1"></i>
                        Добавить менеджера
                    </button>
                </div>
            </div>
            
            <!-- Tab Navigation -->
            <div class="card-body p-0">
                <ul class="nav nav-tabs px-3 pt-3" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button 
                            class="nav-link" 
                            :class="{active: activeTab === 'wallets'}"
                            @click="switchTab('wallets')"
                            type="button"
                        >
                            <i class="fas fa-wallet me-1"></i>
                            Кошельки для операций
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button 
                            class="nav-link" 
                            :class="{active: activeTab === 'managers'}"
                            @click="switchTab('managers')"
                            type="button"
                        >
                            <i class="fas fa-users me-1"></i>
                            Менеджеры
                        </button>
                    </li>
                </ul>
                
                <div class="card-body pt-3">
                    <!-- Status Message -->
                    <div v-if="statusMessage" :class="'alert alert-' + (statusType === 'error' ? 'danger' : 'success')" role="alert">
                        [[ statusMessage ]]
                    </div>
                    
                    <!-- Wallets Tab -->
                    <div v-if="activeTab === 'wallets'">
                        <!-- Loading State -->
                        <div v-if="loading" class="text-center py-4">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Загрузка...</span>
                            </div>
                        </div>
                        
                        <!-- Wallets Table -->
                        <div v-else>
                            <div v-if="wallets.length === 0" class="alert alert-info">
                                Кошельки для сделок не найдены. Добавьте первый кошелек.
                            </div>
                            
                            <div v-else class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>Имя</th>
                                            <th>TRON адрес</th>
                                            <th>Ethereum адрес</th>
                                            <th>Создан</th>
                                            <th>Действия</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="wallet in wallets" :key="wallet.id">
                                            <td>[[ wallet.id ]]</td>
                                            <td>
                                                <div v-if="editingWalletId === wallet.id">
                                                    <div class="input-group input-group-sm">
                                                        <input 
                                                            type="text" 
                                                            class="form-control" 
                                                            v-model="editingWalletName"
                                                            @keyup.enter="saveWalletName(wallet)"
                                                            @keyup.esc="cancelEditingName"
                                                        >
                                                        <button 
                                                            class="btn btn-success btn-sm" 
                                                            @click="saveWalletName(wallet)"
                                                            :disabled="savingName"
                                                        >
                                                            <i class="fas fa-check"></i>
                                                        </button>
                                                        <button 
                                                            class="btn btn-secondary btn-sm" 
                                                            @click="cancelEditingName"
                                                            :disabled="savingName"
                                                        >
                                                            <i class="fas fa-times"></i>
                                                        </button>
                                                    </div>
                                                </div>
                                                <div v-else>
                                                    [[ wallet.name ]]
                                                    <button 
                                                        class="btn btn-link btn-sm p-0 ms-2" 
                                                        @click="startEditingName(wallet)"
                                                        title="Редактировать имя"
                                                    >
                                                        <i class="fas fa-edit"></i>
                                                    </button>
                                                </div>
                                            </td>
                                            <td>
                                                <code class="text-truncate d-inline-block" style="max-width: 150px;" :title="wallet.tron_address">
                                                    [[ wallet.tron_address ]]
                                                </code>
                                                <button 
                                                    class="btn btn-link btn-sm p-0 ms-1" 
                                                    @click="copyToClipboard(wallet.tron_address)"
                                                    title="Копировать адрес"
                                                >
                                                    <i class="fas fa-copy"></i>
                                                </button>
                                                <button 
                                                    class="btn btn-link btn-sm p-0 ms-1" 
                                                    @click="fetchWalletPermissions(wallet)"
                                                    :disabled="loadingPermissions"
                                                    title="Получить permissions из блокчейна"
                                                >
                                                    <i class="fas fa-shield-alt" :class="{'fa-spin': loadingPermissions && permissionsWallet && permissionsWallet.id === wallet.id}"></i>
                                                </button>
                                                <button 
                                                    class="btn btn-link btn-sm p-0 ms-1" 
                                                    @click="showUpdatePermissionsWizard(wallet)"
                                                    title="Настроить permissions"
                                                >
                                                    <i class="fas fa-cog"></i>
                                                </button>
                                            </td>
                                            <td>
                                                <code class="text-truncate d-inline-block" style="max-width: 150px;" :title="wallet.ethereum_address">
                                                    [[ wallet.ethereum_address ]]
                                                </code>
                                                <button 
                                                    class="btn btn-link btn-sm p-0 ms-1" 
                                                    @click="copyToClipboard(wallet.ethereum_address)"
                                                    title="Копировать адрес"
                                                >
                                                    <i class="fas fa-copy"></i>
                                                </button>
                                            </td>
                                            <td>[[ formatDate(wallet.created_at) ]]</td>
                                            <td>
                                                <div class="d-flex gap-1">
                                                    <button 
                                                        class="btn btn-secondary btn-sm" 
                                                        @click="showDidDocModalForWallet(wallet)"
                                                        title="DIDDoc"
                                                    >
                                                        <i class="fas fa-id-card"></i>
                                                    </button>
                                                    <button 
                                                        class="btn btn-danger btn-sm" 
                                                        @click="confirmDelete(wallet)"
                                                        title="Удалить кошелек"
                                                    >
                                                        <i class="fas fa-trash"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Managers Tab -->
                    <div v-if="activeTab === 'managers'">
                        <!-- Loading State -->
                        <div v-if="loadingManagers" class="text-center py-4">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Загрузка...</span>
                            </div>
                        </div>
                        
                        <!-- Managers Table -->
                        <div v-else>
                            <div v-if="managers.length === 0" class="alert alert-info">
                                Менеджеры не найдены. Добавьте первого менеджера.
                            </div>
                            
                            <div v-else class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>Адрес кошелька</th>
                                            <th>Блокчейн</th>
                                            <th>Имя</th>
                                            <th>Верифицирован</th>
                                            <th>Создан</th>
                                            <th>Действия</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="manager in managers" :key="manager.id">
                                            <td>[[ manager.id ]]</td>
                                            <td>
                                                <code class="small">[[ truncateAddress(manager.wallet_address) ]]</code>
                                            </td>
                                            <td>
                                                <span class="badge" :class="{
                                                    'bg-info': manager.blockchain === 'tron',
                                                    'bg-primary': manager.blockchain === 'ethereum',
                                                    'bg-warning': manager.blockchain === 'bitcoin',
                                                    'bg-secondary': !['tron', 'ethereum', 'bitcoin'].includes(manager.blockchain)
                                                }">
                                                    [[ manager.blockchain.toUpperCase() ]]
                                                </span>
                                            </td>
                                            <td>[[ manager.nickname ]]</td>
                                            <td>
                                                <span v-if="manager.is_verified" class="badge bg-success">
                                                    <i class="fas fa-check-circle me-1"></i> Да
                                                </span>
                                                <span v-else class="badge bg-secondary">
                                                    <i class="fas fa-times-circle me-1"></i> Нет
                                                </span>
                                            </td>
                                            <td class="small text-muted">[[ formatDate(manager.created_at) ]]</td>
                                            <td>
                                                <div class="btn-group btn-group-sm">
                                                    <button 
                                                        class="btn btn-outline-primary"
                                                        @click="showEditManagerModal(manager)"
                                                        title="Редактировать"
                                                    >
                                                        <i class="fas fa-edit"></i>
                                                    </button>
                                                    <button 
                                                        class="btn btn-outline-danger"
                                                        @click="confirmDeleteManager(manager)"
                                                        title="Удалить"
                                                    >
                                                        <i class="fas fa-trash"></i>
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Create Wallet Modal -->
            <div v-if="showCreateModal" class="modal fade show" style="display: block; background-color: rgba(0, 0, 0, 0.5);" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content" style="box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">Добавить кошелек</h5>
                            <button type="button" class="btn-close btn-close-white" @click="closeCreateModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div class="mb-3">
                                <label for="walletName" class="form-label">Имя кошелька</label>
                                <input 
                                    type="text" 
                                    class="form-control" 
                                    id="walletName"
                                    v-model="walletForm.name"
                                    placeholder="Введите имя кошелька"
                                >
                            </div>
                            <div class="mb-3">
                                <label for="walletMnemonic" class="form-label">Мнемоническая фраза</label>
                                <textarea 
                                    class="form-control" 
                                    id="walletMnemonic"
                                    v-model="walletForm.mnemonic"
                                    rows="3"
                                    placeholder="Введите мнемоническую фразу (12-24 слова)"
                                ></textarea>
                                <small class="form-text text-muted">
                                    Мнемоническая фраза будет зашифрована и сохранена в базе данных.
                                </small>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closeCreateModal">Отмена</button>
                            <button 
                                type="button" 
                                class="btn btn-primary" 
                                @click="createWallet"
                                :disabled="savingWallet"
                            >
                                <span v-if="savingWallet" class="spinner-border spinner-border-sm me-1"></span>
                                Создать
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Delete Confirmation Modal -->
            <div v-if="walletToDelete" class="modal fade show" style="display: block; background-color: rgba(0, 0, 0, 0.5);" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content" style="box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title">Подтверждение удаления</h5>
                            <button type="button" class="btn-close btn-close-white" @click="cancelDelete"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <p>Вы уверены, что хотите удалить кошелек <strong>[[ walletToDelete.name ]]</strong>?</p>
                            <p class="text-danger"><small>Это действие нельзя отменить.</small></p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="cancelDelete">Отмена</button>
                            <button type="button" class="btn btn-danger" @click="deleteWallet">
                                Удалить
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Create/Edit Manager Modal -->
            <div v-if="showManagerModal" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                [[ editingManager ? 'Редактировать менеджера' : 'Добавить менеджера' ]]
                            </h5>
                            <button type="button" class="btn-close" @click="closeManagerModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div class="mb-3">
                                <label class="form-label">Адрес кошелька</label>
                                <input 
                                    type="text" 
                                    class="form-control font-monospace"
                                    v-model="managerForm.wallet_address"
                                    :disabled="!!editingManager"
                                    placeholder="TXxx... или 0xxx..."
                                />
                                <small class="form-text text-muted">
                                    [[ editingManager ? 'Адрес нельзя изменить' : 'Введите адрес кошелька менеджера' ]]
                                </small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Блокчейн</label>
                                <select class="form-select" v-model="managerForm.blockchain">
                                    <option value="tron">TRON</option>
                                    <option value="ethereum">Ethereum</option>
                                    <option value="bitcoin">Bitcoin</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Имя менеджера</label>
                                <input 
                                    type="text" 
                                    class="form-control"
                                    v-model="managerForm.nickname"
                                    placeholder="Введите имя"
                                    maxlength="100"
                                />
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closeManagerModal">
                                Отмена
                            </button>
                            <button 
                                type="button" 
                                class="btn btn-primary" 
                                @click="saveManager"
                                :disabled="savingManager"
                            >
                                [[ savingManager ? 'Сохранение...' : 'Сохранить' ]]
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Delete Manager Confirmation Modal -->
            <div v-if="managerToDelete" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title">
                                <i class="fas fa-user-times me-2"></i>
                                Отключение прав менеджера
                            </h5>
                            <button type="button" class="btn-close" @click="cancelDeleteManager"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <p>Вы уверены, что хотите отключить права менеджера?</p>
                            <div class="card">
                                <div class="card-body">
                                    <p class="mb-1"><strong>Имя:</strong> [[ managerToDelete.nickname ]]</p>
                                    <p class="mb-1"><strong>Адрес:</strong> <code class="small">[[ managerToDelete.wallet_address ]]</code></p>
                                    <p class="mb-0"><strong>Блокчейн:</strong> [[ managerToDelete.blockchain ]]</p>
                                </div>
                            </div>
                            <div class="alert alert-info mt-3 mb-0">
                                <i class="fas fa-info-circle me-2"></i>
                                Пользователь останется в системе, но потеряет права менеджера. Права можно будет восстановить позже.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="cancelDeleteManager">
                                Отмена
                            </button>
                            <button type="button" class="btn btn-warning" @click="deleteManager">
                                <i class="fas fa-user-times me-1"></i> Отключить права
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Permissions Modal -->
            <div v-if="showPermissionsModal" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-shield-alt me-2"></i>
                                TRON Account Permissions
                            </h5>
                            <button type="button" class="btn-close" @click="closePermissionsModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div v-if="permissionsWallet" class="mb-3">
                                <p class="mb-1"><strong>Кошелек:</strong> [[ permissionsWallet.name ]]</p>
                                <p class="mb-2">
                                    <strong>TRON адрес:</strong> <code>[[ permissionsWallet.tron_address ]]</code>
                                </p>
                                <p class="mb-0">
                                    <a 
                                        :href="getTronscanUrl(permissionsWallet.tron_address)" 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        class="btn btn-sm btn-outline-primary"
                                    >
                                        <i class="fas fa-external-link-alt me-1"></i>
                                        Открыть в Tronscan (Permissions)
                                    </a>
                                </p>
                            </div>
                            
                            <div v-if="loadingPermissions" class="text-center py-4">
                                <div class="spinner-border text-primary"></div>
                                <p class="mt-2">Загрузка permissions из блокчейна...</p>
                            </div>
                            
                            <div v-else-if="!permissionsData" class="alert alert-info">
                                Permissions не загружены. Нажмите кнопку для получения данных из блокчейна.
                            </div>
                            
                            <div v-else>
                                <!-- Owner Permission -->
                                <div v-if="permissionsData.owner" class="mb-4">
                                    <h6 class="mb-3">
                                        <i class="fas fa-key me-2"></i>
                                        Owner Keys (Владельцы)
                                    </h6>
                                    <div class="card">
                                        <div class="card-body">
                                            <p class="mb-2"><strong>Threshold:</strong> [[ permissionsData.owner.threshold || 1 ]]</p>
                                            <p class="mb-2"><strong>Permission Name:</strong> [[ permissionsData.owner.permission_name || 'owner' ]]</p>
                                            <div v-if="permissionsData.owner.keys && permissionsData.owner.keys.length > 0">
                                                <strong>Keys:</strong>
                                                <ul class="list-unstyled mt-2">
                                                    <li v-for="(key, index) in permissionsData.owner.keys" :key="index" class="mb-2">
                                                        <code class="small">[[ getAddressDisplay(key.address) ]]</code>
                                                        <span class="badge bg-secondary ms-2">Weight: [[ key.weight ]]</span>
                                                    </li>
                                                </ul>
                                            </div>
                                            <div v-else class="text-muted">
                                                <small>Нет ключей</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Active Permissions -->
                                <div v-if="permissionsData.active && permissionsData.active.length > 0" class="mb-4">
                                    <h6 class="mb-3">
                                        <i class="fas fa-user-shield me-2"></i>
                                        Active Permissions (Права на операции)
                                    </h6>
                                    <div v-for="(perm, index) in permissionsData.active" :key="index" class="card mb-3">
                                        <div class="card-body">
                                            <p class="mb-2"><strong>Permission ID:</strong> [[ perm.id ]]</p>
                                            <p class="mb-2"><strong>Permission Name:</strong> [[ perm.permission_name || 'active' ]]</p>
                                            <p class="mb-2"><strong>Threshold:</strong> [[ perm.threshold ]]</p>
                                            
                                            <div v-if="perm.operations" class="mb-2">
                                                <strong>Operations:</strong>
                                                <ul class="list-unstyled mt-1">
                                                    <li v-for="(op, opIndex) in getOperationNames(perm.operations)" :key="opIndex" class="small">
                                                        <i class="fas fa-check-circle text-success me-1"></i> [[ op ]]
                                                    </li>
                                                </ul>
                                            </div>
                                            
                                            <div v-if="perm.keys && perm.keys.length > 0">
                                                <strong>Keys:</strong>
                                                <ul class="list-unstyled mt-2">
                                                    <li v-for="(key, keyIndex) in perm.keys" :key="keyIndex" class="mb-2">
                                                        <code class="small">[[ getAddressDisplay(key.address) ]]</code>
                                                        <span class="badge bg-info ms-2">Weight: [[ key.weight ]]</span>
                                                    </li>
                                                </ul>
                                            </div>
                                            <div v-else class="text-muted">
                                                <small>Нет ключей</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div v-else class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    Активные permissions не найдены
                                </div>
                                
                                <!-- Witness Permission -->
                                <div v-if="permissionsData.witness" class="mb-4">
                                    <h6 class="mb-3">
                                        <i class="fas fa-certificate me-2"></i>
                                        Witness Permission
                                    </h6>
                                    <div class="card">
                                        <div class="card-body">
                                            <p class="mb-2"><strong>Permission Name:</strong> [[ permissionsData.witness.permission_name || 'witness' ]]</p>
                                            <div v-if="permissionsData.witness.keys && permissionsData.witness.keys.length > 0">
                                                <strong>Keys:</strong>
                                                <ul class="list-unstyled mt-2">
                                                    <li v-for="(key, index) in permissionsData.witness.keys" :key="index" class="mb-2">
                                                        <code class="small">[[ getAddressDisplay(key.address) ]]</code>
                                                        <span class="badge bg-secondary ms-2">Weight: [[ key.weight ]]</span>
                                                    </li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closePermissionsModal">
                                Закрыть
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Update Permissions Wizard Modal -->
            <div v-if="showUpdatePermissionsModal" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-cog me-2"></i>
                                Мастер конфигурации Permissions
                            </h5>
                            <button type="button" class="btn-close btn-close-white" @click="closeUpdatePermissionsModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div v-if="updatePermissionsWallet" class="mb-4">
                                <p class="mb-1"><strong>Кошелек:</strong> [[ updatePermissionsWallet.name ]]</p>
                                <p class="mb-0"><strong>TRON адрес:</strong> <code>[[ updatePermissionsWallet.tron_address ]]</code></p>
                            </div>
                            
                            <!-- Transaction Result -->
                            <div v-if="updateTxResult && !updateTxFinalResult" class="alert alert-success mb-4">
                                <h6><i class="fas fa-check-circle me-2"></i>Транзакция создана успешно!</h6>
                                <p class="mb-1"><strong>TX ID:</strong> <code>[[ updateTxResult.tx_id ]]</code></p>
                                <p class="mb-0"><small>Транзакция требует подписи для отправки в блокчейн.</small></p>
                            </div>
                            
                            <!-- TronSign Component (hidden, used only for logic) -->
                            <tron-sign 
                                ref="updatePermissionsTronSign"
                                @signing="onUpdatePermissionsSigning"
                                @signed="onUpdatePermissionsSigned"
                                @error="onUpdatePermissionsError"
                            ></tron-sign>
                            
                            <!-- Signing Section -->
                            <div v-if="updateTxResult && updateTxUnsignedTransaction && !updateTxFinalResult" class="card border-primary mb-4">
                                <div class="card-header bg-primary text-white">
                                    <h6 class="mb-0">
                                        <i class="fas fa-signature me-2"></i>
                                        Подпись транзакции через TronLink
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div class="alert alert-info mb-3">
                                        <p class="mb-1"><strong>TX ID:</strong> <code>[[ updateTxResult.tx_id ]]</code></p>
                                        <p class="mb-0">Готово к подписанию через TronLink</p>
                                    </div>
                                    <button 
                                        class="btn btn-success w-100"
                                        @click="signUpdatePermissionsTransaction"
                                        :disabled="updateTxSigning || updateTxBroadcasting"
                                    >
                                        <span v-if="updateTxSigning" class="spinner-border spinner-border-sm me-2"></span>
                                        <span v-else-if="updateTxBroadcasting" class="spinner-border spinner-border-sm me-2"></span>
                                        <i v-else class="fas fa-paper-plane me-2"></i>
                                        [[ updateTxSigning ? 'Подписание...' : updateTxBroadcasting ? 'Отправка...' : 'Подписать и отправить транзакцию' ]]
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Final Result -->
                            <div v-if="updateTxFinalResult" class="alert mb-4" :class="updateTxFinalResult.success ? 'alert-success' : 'alert-danger'">
                                <h6>
                                    <i :class="updateTxFinalResult.success ? 'fas fa-check-circle' : 'fas fa-times-circle'" class="me-2"></i>
                                    [[ updateTxFinalResult.message ]]
                                </h6>
                                <div v-if="updateTxFinalResult.success && updateTxFinalResult.txId" class="mt-3">
                                    <p class="mb-2"><strong>TX ID:</strong></p>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <code class="small">[[ updateTxFinalResult.txId ]]</code>
                                        <button 
                                            class="btn btn-sm btn-outline-primary ms-2"
                                            @click="copyToClipboard(updateTxFinalResult.txId)"
                                            title="Копировать TX ID"
                                        >
                                            <i class="fas fa-copy"></i>
                                        </button>
                                    </div>
                                    <div class="mt-3">
                                        <a 
                                            :href="getTronScanUrl(updateTxFinalResult.txId)"
                                            target="_blank"
                                            class="btn btn-primary"
                                        >
                                            <i class="fas fa-external-link-alt me-2"></i>
                                            Посмотреть в TronScan
                                        </a>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Configuration Form -->
                            <div class="mb-3">
                                <label class="form-label">Threshold (Порог подписей)</label>
                                <input 
                                    type="number" 
                                    class="form-control"
                                    v-model.number="updatePermissionsForm.threshold"
                                    min="1"
                                    :max="getTotalWeight()"
                                />
                                <small class="form-text text-muted">
                                    Минимальное количество подписей для выполнения операций
                                </small>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Имя permission</label>
                                <input 
                                    type="text" 
                                    class="form-control"
                                    v-model="updatePermissionsForm.permission_name"
                                    placeholder="multisig"
                                />
                            </div>
                            
                            <!-- Weight Validation -->
                            <div class="mb-3">
                                <div :class="'alert ' + (isWeightValid() ? 'alert-success' : 'alert-danger')">
                                    <i :class="isWeightValid() ? 'fas fa-check-circle' : 'fas fa-exclamation-triangle'" class="me-2"></i>
                                    [[ getWeightValidationMessage() ]]
                                </div>
                            </div>
                            
                            <!-- Keys List -->
                            <div class="mb-3">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <label class="form-label mb-0">Ключи (Адреса менеджеров)</label>
                                    <button 
                                        class="btn btn-sm btn-primary" 
                                        @click="addPermissionKey"
                                        :disabled="loadingManagers"
                                    >
                                        <i class="fas fa-plus me-1"></i> Добавить ключ
                                    </button>
                                </div>
                                
                                <div v-if="loadingManagers" class="text-center py-2">
                                    <div class="spinner-border spinner-border-sm"></div>
                                    <small class="d-block mt-1">Загрузка менеджеров...</small>
                                </div>
                                
                                <div v-else-if="updatePermissionsForm.keys.length === 0" class="alert alert-info">
                                    Добавьте хотя бы один ключ
                                </div>
                                
                                <div v-else class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th style="width: 50px;">#</th>
                                                <th>Адрес</th>
                                                <th style="width: 120px;">Вес</th>
                                                <th style="width: 80px;">Действие</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="(key, index) in updatePermissionsForm.keys" :key="index">
                                                <td>[[ index + 1 ]]</td>
                                                <td>
                                                    <select 
                                                        v-if="!key.isOwner"
                                                        class="form-select form-select-sm"
                                                        v-model="key.address"
                                                    >
                                                        <option value="">Выберите адрес...</option>
                                                        <option 
                                                            v-for="manager in availableManagers" 
                                                            :key="manager.id || manager.wallet_address"
                                                            :value="manager.wallet_address"
                                                        >
                                                            [[ manager.is_owner ? '👑 Owner: ' : '' ]][[ manager.nickname ]] ([[ manager.wallet_address ]])
                                                        </option>
                                                    </select>
                                                    <div v-else class="d-flex align-items-center">
                                                        <code class="small me-2">[[ key.address ]]</code>
                                                        <span class="badge bg-warning text-dark">
                                                            <i class="fas fa-crown"></i> Owner
                                                        </span>
                                                    </div>
                                                    <small v-if="key.address && !validateWalletAddress(key.address, 'tron')" class="text-danger">
                                                        Неверный формат TRON адреса
                                                    </small>
                                                </td>
                                                <td>
                                                    <input 
                                                        type="number" 
                                                        class="form-control form-control-sm"
                                                        v-model.number="key.weight"
                                                        min="1"
                                                        step="1"
                                                    />
                                                </td>
                                                <td>
                                                    <button 
                                                        v-if="!key.isOwner"
                                                        class="btn btn-sm btn-danger"
                                                        @click="removePermissionKey(index)"
                                                        title="Удалить"
                                                    >
                                                        <i class="fas fa-trash"></i>
                                                    </button>
                                                    <span v-else class="badge bg-warning text-dark" title="Ключ владельца (Owner) - нельзя удалить">
                                                        <i class="fas fa-crown"></i> Owner
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            
                            <!-- Operations Info -->
                            <div class="mb-3">
                                <div class="card bg-light">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            <i class="fas fa-info-circle me-2"></i>
                                            Операции
                                        </h6>
                                        <p class="card-text mb-0">
                                            <small>
                                                Настроено: <strong>каноническая маска операций</strong> (стандартный набор разрешенных операций TRON)
                                            </small>
                                        </p>
                                        <input 
                                            type="text" 
                                            class="form-control form-control-sm mt-2 font-monospace"
                                            v-model="updatePermissionsForm.operations"
                                            readonly
                                            title="Hex строка операций (каноническая маска)"
                                        />
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Summary -->
                            <div class="card bg-info text-white mb-3">
                                <div class="card-body">
                                    <h6 class="card-title">Сводка</h6>
                                    <ul class="mb-0">
                                        <li>Ключей: [[ updatePermissionsForm.keys.length ]]</li>
                                        <li>Сумма весов: [[ getTotalWeight() ]]</li>
                                        <li>Threshold: [[ updatePermissionsForm.threshold ]]</li>
                                        <li>Операции: каноническая маска</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closeUpdatePermissionsModal">
                                Отмена
                            </button>
                            <button 
                                type="button" 
                                class="btn btn-primary" 
                                @click="createUpdatePermissionsTransaction"
                                :disabled="creatingUpdateTx || !isWeightValid() || updatePermissionsForm.keys.length === 0"
                            >
                                <span v-if="creatingUpdateTx" class="spinner-border spinner-border-sm me-2"></span>
                                <i v-else class="fas fa-cog me-2"></i>
                                [[ creatingUpdateTx ? 'Создание...' : 'Создать транзакцию' ]]
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- DIDDoc Modal -->
            <did-doc-modal 
                :show="showDidDocModalFlag"
                :user-id="didDocUserId"
                :owner-info="didDocOwnerInfo"
                :use-admin-endpoint="true"
                @close="closeDidDocModal"
            ></did-doc-modal>
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
         * Detect browser type
         */
        detectBrowser() {
            const userAgent = navigator.userAgent;
            
            if (userAgent.indexOf("Edg") > -1) {
                return "Edge";
            } else if (userAgent.indexOf("Chrome") > -1) {
                return "Chrome";
            } else if (userAgent.indexOf("Safari") > -1) {
                return "Safari";
            } else if (userAgent.indexOf("Firefox") > -1) {
                return "Firefox";
            } else if (userAgent.indexOf("MSIE") > -1 || userAgent.indexOf("Trident") > -1) {
                return "IE";
            }
            
            return "Unknown";
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
                const browser = this.detectBrowser();
                let statusMsg = 'Установите TronLink или TrustWallet';
                
                if (browser === 'Edge' || browser === 'IE') {
                    statusMsg = 'Для Microsoft Edge: Установите расширение TronLink из Microsoft Store. После установки обновите страницу (F5).';
                }
                
                this.showStatus(statusMsg, 'info');
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
                console.log('Signing message:', message);
                console.log('With address:', address);
                
                // Для совместимости с разными браузерами (особенно Edge)
                // используем разные методы подписи в зависимости от доступного API
                
                let signature;
                
                // Метод 1: Попытка использовать tronWeb.trx.signMessageV2 (более новый API)
                if (typeof window.tronWeb.trx.signMessageV2 === 'function') {
                    try {
                        console.log('Trying signMessageV2...');
                        signature = await window.tronWeb.trx.signMessageV2(message);
                        console.log('signMessageV2 success:', signature);
                        return signature;
                    } catch (e) {
                        console.log('signMessageV2 failed:', e);
                    }
                }
                
                // Метод 2: Использование tronWeb.trx.sign (стандартный метод)
                if (typeof window.tronWeb.trx.sign === 'function') {
                    try {
                        console.log('Trying trx.sign...');
                        // Конвертируем сообщение в UTF-8 строку для корректной подписи
                        const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
                        signature = await window.tronWeb.trx.sign(messageStr);
                        console.log('trx.sign success:', signature);
                        return signature;
                    } catch (e) {
                        console.log('trx.sign failed:', e);
                        throw e;
                    }
                }
                
                // Метод 3: Через tronLink API (для расширения TronLink)
                if (window.tronLink && typeof window.tronLink.request === 'function') {
                    try {
                        console.log('Trying tronLink.request...');
                        const messageHex = window.tronWeb.toHex(message);
                        signature = await window.tronLink.request({
                            method: 'tron_signMessage',
                            params: {
                                message: messageHex,
                                address: address
                            }
                        });
                        console.log('tronLink.request success:', signature);
                        return signature;
                    } catch (e) {
                        console.log('tronLink.request failed:', e);
                        throw e;
                    }
                }
                
                throw new Error('Не удалось найти метод для подписи сообщения');
                
            } catch (error) {
                console.error('Sign message error:', error);
                if (error.message && error.message.includes('Confirmation declined')) {
                    this.showStatus('Подпись сообщения отклонена.', 'error');
                } else if (error.message && error.message.includes('Invalid transaction')) {
                    this.showStatus('Ошибка подписи. Попробуйте обновить страницу и разблокировать кошелек.', 'error');
                } else {
                    this.showStatus(`Ошибка подписи: ${error.message || 'undefined'}`, 'error');
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
            // Remove from cookies
            document.cookie = 'tron_auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            // Remove from localStorage (used on main page)
            localStorage.removeItem('access_token');
            localStorage.removeItem('wallet_address');
            
            console.log('TronAuth: Tokens removed from cookies and localStorage');
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
                        const requestParams = { 
                            method: 'tron_requestAccounts' 
                        };
                        
                        // Для TrustWallet на мобильных устройствах добавляем версию DApp
                        if (this.isMobileDevice) {
                            requestParams.dappVersion = '1.0.0';
                        }
                        
                        const accounts = await window.tronWeb.request(requestParams);
                        console.log('Request result:', accounts);
                    } catch (requestError) {
                        console.log('tronWeb.request failed:', requestError);
                    }
                }
                
                // Метод 2: Проверяем tronLink API (для TronLink расширения)
                if (window.tronLink && !window.tronLink.ready) {
                    try {
                        console.log('Requesting tronLink...');
                        const requestParams = { method: 'tron_requestAccounts' };
                        
                        // Для TrustWallet на мобильных устройствах добавляем версию DApp
                        if (this.isMobileDevice) {
                            requestParams.dappVersion = '1.0.0';
                        }
                        
                        const res = await window.tronLink.request(requestParams);
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
                
                // Более детальная обработка ошибок для разных браузеров
                let errorMessage = 'Ошибка подключения';
                
                if (error.message) {
                    if (error.message.includes('User rejected')) {
                        errorMessage = 'Подключение отклонено пользователем';
                    } else if (error.message.includes('Invalid transaction')) {
                        errorMessage = 'Ошибка транзакции. Убедитесь, что TronLink разблокирован и обновите страницу';
                    } else if (error.message.includes('Confirmation declined')) {
                        errorMessage = 'Подпись отклонена';
                    } else if (error.message.includes('timeout')) {
                        errorMessage = 'Время ожидания истекло. Попробуйте снова';
                    } else {
                        errorMessage = `Ошибка: ${error.message}`;
                    }
                }
                
                this.showStatus(errorMessage, 'error');
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
            // Check localStorage first (used on main page)
            const localToken = localStorage.getItem('access_token');
            const localWalletAddress = localStorage.getItem('wallet_address');
            
            if (localToken && localWalletAddress) {
                try {
                    const response = await fetch(`${this.apiBase}/auth/tron/me`, {
                        headers: {
                            'Authorization': `Bearer ${localToken}`
                        }
                    });

                    if (response.ok) {
                        const userInfo = await response.json();
                        this.walletAddress = userInfo.wallet_address;
                        this.isAuthenticated = true;
                        console.log('TronAuth: Restored session from localStorage');
                        return;
                    } else {
                        // Token is invalid, clear localStorage
                        console.log('TronAuth: Invalid token in localStorage, clearing...');
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('wallet_address');
                    }
                } catch (error) {
                    console.error('Error checking auth from localStorage:', error);
                    // Clear invalid tokens
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('wallet_address');
                }
            }
            
            // Fallback to cookies check (for backward compatibility)
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
                        // Don't set isAuthenticated = true, just store the address
                    }
                } catch (error) {
                    console.error('Error checking TronWeb:', error);
                }
            }
            
            // Ensure component is in clean state if no valid auth found
            if (!this.isAuthenticated) {
                this.walletAddress = null;
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

// WalletUsers Management Component
Vue.component('WalletUsers', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            loading: true,
            users: [],
            total: 0,
            page: 1,
            pageSize: 20,
            searchQuery: '',
            blockchainFilter: '',
            
            // Create/Edit user modal
            showUserModal: false,
            editingUser: null,
            userForm: {
                wallet_address: '',
                blockchain: 'tron',
                nickname: '',
                is_verified: false,
                access_to_admin_panel: false
            },
            savingUser: false,
            
            // Delete confirmation
            userToDelete: null,
            
            // Billing modal
            showBillingModal: false,
            billingUser: null,
            billingForm: {
                amount: '',
                isDeposit: true
            },
            savingBilling: false,
            
            // Billing history modal
            showBillingHistoryModal: false,
            billingHistoryUser: null,
            billingHistory: [],
            billingHistoryLoading: false,
            billingHistoryPage: 1,
            billingHistoryTotal: 0,
            
            // DIDDoc modal
            showDidDocModalFlag: false,
            didDocUserId: null,
            didDocOwnerInfo: null,
            
            statusMessage: '',
            statusType: ''
        };
    },
    computed: {
        totalPages() {
            return Math.ceil(this.total / this.pageSize);
        },
        paginationPages() {
            const pages = [];
            const maxVisible = 5;
            let start = Math.max(1, this.page - Math.floor(maxVisible / 2));
            let end = Math.min(this.totalPages, start + maxVisible - 1);
            
            if (end - start < maxVisible - 1) {
                start = Math.max(1, end - maxVisible + 1);
            }
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        }
    },
    mounted() {
        this.loadUsers();
    },
    methods: {
        async loadUsers() {
            this.loading = true;
            try {
                const params = new URLSearchParams({
                    page: this.page,
                    page_size: this.pageSize
                });
                
                if (this.searchQuery) {
                    params.append('query', this.searchQuery);
                }
                if (this.blockchainFilter) {
                    params.append('blockchain', this.blockchainFilter);
                }
                
                const response = await fetch('/api/admin/wallet-users?' + params);
                
                if (!response.ok) {
                    throw new Error('Failed to load users');
                }
                
                const data = await response.json();
                this.users = data.users;
                this.total = data.total;
                
            } catch (error) {
                console.error('Error loading users:', error);
                this.showStatus('Ошибка загрузки пользователей: ' + error.message, 'error');
            } finally {
                this.loading = false;
            }
        },
        
        search() {
            this.page = 1;
            this.loadUsers();
        },
        
        filterByBlockchain(blockchain) {
            this.blockchainFilter = blockchain;
            this.page = 1;
            this.loadUsers();
        },
        
        clearFilters() {
            this.searchQuery = '';
            this.blockchainFilter = '';
            this.page = 1;
            this.loadUsers();
        },
        
        goToPage(pageNum) {
            this.page = pageNum;
            this.loadUsers();
        },
        
        showCreateModal() {
            this.editingUser = null;
            this.userForm = {
                wallet_address: '',
                blockchain: 'tron',
                nickname: '',
                is_verified: false,
                access_to_admin_panel: false
            };
            this.showUserModal = true;
        },
        
        showEditModal(user) {
            this.editingUser = user;
            this.userForm = {
                wallet_address: user.wallet_address,
                blockchain: user.blockchain,
                nickname: user.nickname,
                is_verified: user.is_verified || false,
                access_to_admin_panel: user.access_to_admin_panel || false
            };
            this.showUserModal = true;
        },
        
        showBillingModalForUser(user) {
            this.billingUser = user;
            this.billingForm = {
                amount: '',
                isDeposit: true
            };
            this.showBillingModal = true;
        },
        
        closeBillingModal() {
            this.showBillingModal = false;
            this.billingUser = null;
            this.billingForm = {
                amount: '',
                isDeposit: true
            };
        },
        
        async saveBilling() {
            if (!this.billingForm.amount || parseFloat(this.billingForm.amount) <= 0) {
                this.showStatus('Введите корректную сумму', 'error');
                return;
            }
            
            this.savingBilling = true;
            
            try {
                const amount = this.billingForm.isDeposit 
                    ? parseFloat(this.billingForm.amount)
                    : -parseFloat(this.billingForm.amount);
                
                const response = await fetch(`/api/admin/billing/users/${this.billingUser.id}/transactions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        usdt_amount: amount
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to create transaction');
                }
                
                this.showStatus(
                    this.billingForm.isDeposit ? 'Баланс пополнен' : 'Баланс списан',
                    'success'
                );
                this.closeBillingModal();
                await this.loadUsers();
                // Обновить историю биллинга, если модальное окно открыто
                if (this.showBillingHistoryModal && this.billingHistoryUser && this.billingHistoryUser.id === this.billingUser.id) {
                    await this.loadBillingHistory();
                }
                
            } catch (error) {
                console.error('Error saving billing:', error);
                this.showStatus('Ошибка операции: ' + error.message, 'error');
            } finally {
                this.savingBilling = false;
            }
        },
        
        async showBillingHistory(user) {
            this.billingHistoryUser = {...user}; // Копируем объект, чтобы обновлять баланс
            this.billingHistoryPage = 1;
            this.showBillingHistoryModal = true;
            await this.loadBillingHistory();
            // Обновить данные пользователя для актуального баланса
            await this.loadUsers();
        },
        
        async loadBillingHistory() {
            if (!this.billingHistoryUser) return;
            
            this.billingHistoryLoading = true;
            try {
                const params = new URLSearchParams({
                    page: this.billingHistoryPage,
                    page_size: 20
                });
                
                const response = await fetch(`/api/admin/billing/users/${this.billingHistoryUser.id}/transactions?${params}`);
                
                if (!response.ok) {
                    throw new Error('Failed to load billing history');
                }
                
                const data = await response.json();
                this.billingHistory = data.transactions;
                this.billingHistoryTotal = data.total;
                
                // Обновить баланс пользователя из списка, если модальное окно открыто
                if (this.showBillingHistoryModal && this.billingHistoryUser) {
                    const updatedUser = this.users.find(u => u.id === this.billingHistoryUser.id);
                    if (updatedUser) {
                        this.billingHistoryUser.balance_usdt = updatedUser.balance_usdt;
                    }
                }
                
            } catch (error) {
                console.error('Error loading billing history:', error);
                this.showStatus('Ошибка загрузки истории: ' + error.message, 'error');
            } finally {
                this.billingHistoryLoading = false;
            }
        },
        
        goToBillingHistoryPage(pageNum) {
            this.billingHistoryPage = pageNum;
            this.loadBillingHistory();
        },
        
        getBillingHistoryTotalPages() {
            return Math.ceil(this.billingHistoryTotal / 20);
        },
        
        getBillingHistoryPaginationPages() {
            const pages = [];
            const totalPages = this.getBillingHistoryTotalPages();
            const maxVisible = 5;
            let start = Math.max(1, this.billingHistoryPage - Math.floor(maxVisible / 2));
            let end = Math.min(totalPages, start + maxVisible - 1);
            
            if (end - start < maxVisible - 1) {
                start = Math.max(1, end - maxVisible + 1);
            }
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        },
        
        closeBillingHistoryModal() {
            this.showBillingHistoryModal = false;
            this.billingHistoryUser = null;
            this.billingHistory = [];
            this.billingHistoryPage = 1;
        },
        
        formatCurrency(amount) {
            return new Intl.NumberFormat('ru-RU', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 8
            }).format(amount);
        },
        
        closeUserModal() {
            this.showUserModal = false;
            this.editingUser = null;
            this.userForm = {
                wallet_address: '',
                blockchain: 'tron',
                nickname: '',
                is_verified: false,
                access_to_admin_panel: false
            };
        },
        
        async saveUser() {
            if (!this.userForm.wallet_address || !this.userForm.blockchain || !this.userForm.nickname) {
                this.showStatus('Заполните все поля', 'error');
                return;
            }
            
            // Валидация адреса кошелька (только при создании нового пользователя)
            if (!this.editingUser) {
                if (!this.validateWalletAddress(this.userForm.wallet_address, this.userForm.blockchain)) {
                    const blockchainName = this.userForm.blockchain === 'tron' ? 'TRON' : 'Ethereum';
                    const expectedFormat = this.userForm.blockchain === 'tron' 
                        ? '34 символа, начинается с T (например: TRCW29HRORXWcw3PoEEaQzZaRLiZjbkFnS)'
                        : '42 символа, начинается с 0x (например: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb)';
                    this.showStatus(`Неверный формат адреса ${blockchainName}. Ожидается: ${expectedFormat}`, 'error');
                    return;
                }
            }
            
            this.savingUser = true;
            
            try {
                const url = this.editingUser 
                    ? '/api/admin/wallet-users/' + this.editingUser.id
                    : '/api/admin/wallet-users';
                
                const method = this.editingUser ? 'PUT' : 'POST';
                
                const body = this.editingUser
                    ? {
                        nickname: this.userForm.nickname,
                        blockchain: this.userForm.blockchain,
                        is_verified: this.userForm.is_verified,
                        access_to_admin_panel: this.userForm.access_to_admin_panel
                    }
                    : this.userForm;
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(body)
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save user');
                }
                
                this.showStatus(
                    this.editingUser ? 'Пользователь обновлен' : 'Пользователь создан',
                    'success'
                );
                this.closeUserModal();
                this.loadUsers();
                
            } catch (error) {
                console.error('Error saving user:', error);
                this.showStatus('Ошибка сохранения: ' + error.message, 'error');
            } finally {
                this.savingUser = false;
            }
        },
        
        confirmDelete(user) {
            this.userToDelete = user;
        },
        
        cancelDelete() {
            this.userToDelete = null;
        },
        
        async deleteUser() {
            if (!this.userToDelete) return;
            
            try {
                const response = await fetch('/api/admin/wallet-users/' + this.userToDelete.id, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    throw new Error('Failed to delete user');
                }
                
                this.showStatus('Пользователь удален', 'success');
                this.userToDelete = null;
                this.loadUsers();
                
            } catch (error) {
                console.error('Error deleting user:', error);
                this.showStatus('Ошибка удаления: ' + error.message, 'error');
            }
        },
        
        showStatus(message, type) {
            this.statusMessage = message;
            this.statusType = type;
            setTimeout(() => {
                this.statusMessage = '';
                this.statusType = '';
            }, 3000);
        },
        
        formatDate(dateString) {
            return new Date(dateString).toLocaleString('ru-RU');
        },
        
        truncateAddress(address) {
            if (!address || address.length <= 16) return address;
            return address.substring(0, 8) + '...' + address.substring(address.length - 6);
        },
        
        validateWalletAddress(address, blockchain) {
            if (!address || typeof address !== 'string') {
                return false;
            }
            
            const trimmedAddress = address.trim();
            
            if (blockchain === 'tron') {
                // TRON адреса начинаются с 'T', длина 34 символа
                if (trimmedAddress.length !== 34) {
                    return false;
                }
                if (!trimmedAddress.startsWith('T')) {
                    return false;
                }
                // Проверка на Base58 символы (1-9, A-H, J-N, P-Z, a-k, m-z)
                const base58Regex = /^[1-9A-HJ-NP-Za-km-z]+$/;
                return base58Regex.test(trimmedAddress);
            } else if (blockchain === 'ethereum') {
                // Ethereum адреса начинаются с '0x', длина 42 символа
                if (trimmedAddress.length !== 42) {
                    return false;
                }
                if (!trimmedAddress.startsWith('0x') && !trimmedAddress.startsWith('0X')) {
                    return false;
                }
                // Проверка на hex символы (0-9, a-f, A-F)
                const hexRegex = /^0x[0-9a-fA-F]{40}$/;
                return hexRegex.test(trimmedAddress);
            }
            
            return false;
        },
        
        showDidDocModal(user) {
            this.didDocUserId = user.id;
            this.didDocOwnerInfo = {
                nickname: user.nickname,
                avatar: user.avatar
            };
            this.showDidDocModalFlag = true;
        },
        
        closeDidDocModal() {
            this.showDidDocModalFlag = false;
            this.didDocUserId = null;
            this.didDocOwnerInfo = null;
        }
    },
    
    template: `
        <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <i class="fas fa-users me-2"></i>
                    Управление пользователями
                </div>
                <button class="btn btn-sm btn-primary" @click="showCreateModal">
                    <i class="fas fa-plus me-1"></i> Добавить пользователя
                </button>
            </div>
            
            <div class="card-body">
                <!-- Status Message -->
                <div v-if="statusMessage" 
                     :class="'alert alert-' + (statusType === 'error' ? 'danger' : 'success')"
                     style="border-radius: 10px;">
                    [[ statusMessage ]]
                </div>
                
                <!-- Search and Filter -->
                <div class="row mb-3">
                    <div class="col-md-6">
                        <div class="input-group">
                            <input 
                                type="text" 
                                class="form-control" 
                                placeholder="Поиск по адресу или имени..."
                                v-model="searchQuery"
                                @keyup.enter="search"
                            />
                            <button class="btn btn-outline-primary" @click="search">
                                <i class="fas fa-search"></i>
                            </button>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <select class="form-select" v-model="blockchainFilter" @change="filterByBlockchain(blockchainFilter)">
                            <option value="">Все блокчейны</option>
                            <option value="tron">TRON</option>
                            <option value="ethereum">Ethereum</option>
                            <option value="bitcoin">Bitcoin</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-outline-secondary w-100" @click="clearFilters">
                            <i class="fas fa-times me-1"></i> Сбросить
                        </button>
                    </div>
                </div>
                
                <!-- Loading State -->
                <div v-if="loading" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                </div>
                
                <!-- Users Table -->
                <div v-else-if="users.length > 0">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th style="width: 50px;">ID</th>
                                    <th>Адрес кошелька</th>
                                    <th style="width: 100px;">Блокчейн</th>
                                    <th style="width: 200px;">Имя</th>
                                    <th style="width: 120px;">Верифицирован</th>
                                    <th style="width: 140px;">Доступ к панели</th>
                                    <th style="width: 120px;">Баланс USDT</th>
                                    <th style="width: 150px;">Создан</th>
                                    <th style="width: 200px;" class="text-end">Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="user in users" :key="user.id">
                                    <td>[[ user.id ]]</td>
                                    <td>
                                        <code class="small">[[ truncateAddress(user.wallet_address) ]]</code>
                                    </td>
                                    <td>
                                        <span class="badge" :class="{
                                            'bg-info': user.blockchain === 'tron',
                                            'bg-primary': user.blockchain === 'ethereum',
                                            'bg-warning': user.blockchain === 'bitcoin',
                                            'bg-secondary': !['tron', 'ethereum', 'bitcoin'].includes(user.blockchain)
                                        }">
                                            [[ user.blockchain.toUpperCase() ]]
                                        </span>
                                    </td>
                                    <td>[[ user.nickname ]]</td>
                                    <td>
                                        <span v-if="user.is_verified" class="badge bg-success" title="Агент прошел верификацию документов">
                                            <i class="fas fa-check-circle me-1"></i> Да
                                        </span>
                                        <span v-else class="badge bg-secondary" title="Агент не прошел верификацию документов">
                                            <i class="fas fa-times-circle me-1"></i> Нет
                                        </span>
                                    </td>
                                    <td>
                                        <span v-if="user.access_to_admin_panel" class="badge bg-primary" title="Пользователь имеет доступ к админ-панели ноды">
                                            <i class="fas fa-shield-alt me-1"></i> Да
                                        </span>
                                        <span v-else class="badge bg-secondary" title="Пользователь не имеет доступа к админ-панели ноды">
                                            <i class="fas fa-ban me-1"></i> Нет
                                        </span>
                                    </td>
                                    <td>
                                        <span class="badge bg-info">
                                            [[ formatCurrency(user.balance_usdt || 0) ]] USDT
                                        </span>
                                    </td>
                                    <td class="small text-muted">[[ formatDate(user.created_at) ]]</td>
                                    <td class="text-end">
                                        <div class="d-flex gap-1">
                                            <button 
                                                class="btn btn-outline-primary btn-sm"
                                                @click="showEditModal(user)"
                                                title="Редактировать"
                                            >
                                                <i class="fas fa-edit"></i>
                                            </button>
                                            <button 
                                                class="btn btn-outline-success btn-sm"
                                                @click="showBillingModalForUser(user)"
                                                title="Пополнить/Списать баланс"
                                            >
                                                <i class="fas fa-wallet"></i>
                                            </button>
                                            <button 
                                                class="btn btn-outline-info btn-sm"
                                                @click="showBillingHistory(user)"
                                                title="История операций"
                                            >
                                                <i class="fas fa-history"></i>
                                            </button>
                                            <button 
                                                class="btn btn-outline-secondary btn-sm"
                                                @click="showDidDocModal(user)"
                                                title="DIDDoc"
                                            >
                                                <i class="fas fa-id-card"></i>
                                            </button>
                                            <button 
                                                class="btn btn-outline-danger btn-sm"
                                                @click="confirmDelete(user)"
                                                title="Удалить"
                                            >
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- Pagination -->
                    <nav v-if="totalPages > 1" class="mt-3">
                        <ul class="pagination justify-content-center">
                            <li class="page-item" :class="{disabled: page === 1}">
                                <a class="page-link" @click.prevent="goToPage(page - 1)" href="#">
                                    <i class="fas fa-chevron-left"></i>
                                </a>
                            </li>
                            <li class="page-item" v-for="pageNum in paginationPages" :key="pageNum" :class="{active: page === pageNum}">
                                <a class="page-link" @click.prevent="goToPage(pageNum)" href="#">
                                    [[ pageNum ]]
                                </a>
                            </li>
                            <li class="page-item" :class="{disabled: page === totalPages}">
                                <a class="page-link" @click.prevent="goToPage(page + 1)" href="#">
                                    <i class="fas fa-chevron-right"></i>
                                </a>
                            </li>
                        </ul>
                        <p class="text-center text-muted small">
                            Показано [[ users.length ]] из [[ total ]] пользователей
                        </p>
                    </nav>
                </div>
                
                <!-- Empty State -->
                <div v-else class="text-center py-5 text-muted">
                    <i class="fas fa-users fa-3x mb-3 opacity-50"></i>
                    <p>Пользователи не найдены</p>
                    <button class="btn btn-primary mt-2" @click="showCreateModal">
                        <i class="fas fa-plus me-1"></i> Добавить первого пользователя
                    </button>
                </div>
            </div>
            
            <!-- Create/Edit User Modal -->
            <div v-if="showUserModal" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                [[ editingUser ? 'Редактировать пользователя' : 'Добавить пользователя' ]]
                            </h5>
                            <button type="button" class="btn-close" @click="closeUserModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div class="mb-3">
                                <label class="form-label">Адрес кошелька</label>
                                <input 
                                    type="text" 
                                    class="form-control font-monospace"
                                    v-model="userForm.wallet_address"
                                    :disabled="!!editingUser"
                                    placeholder="TXxx... или 0xxx..."
                                />
                                <small class="form-text text-muted">
                                    [[ editingUser ? 'Адрес нельзя изменить' : 'Введите адрес кошелька пользователя' ]]
                                </small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Блокчейн</label>
                                <select class="form-select" v-model="userForm.blockchain">
                                    <option value="tron">TRON</option>
                                    <option value="ethereum">Ethereum</option>
                                    <option value="bitcoin">Bitcoin</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Имя пользователя</label>
                                <input 
                                    type="text" 
                                    class="form-control"
                                    v-model="userForm.nickname"
                                    placeholder="Введите имя"
                                    maxlength="100"
                                />
                            </div>
                            <div class="mb-3">
                                <div class="form-check mb-2">
                                    <input 
                                        class="form-check-input" 
                                        type="checkbox" 
                                        v-model="userForm.is_verified"
                                        id="is_verified_check"
                                    />
                                    <label class="form-check-label" for="is_verified_check">
                                        Пользователь верифицирован (проверены документы)
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input 
                                        class="form-check-input" 
                                        type="checkbox" 
                                        v-model="userForm.access_to_admin_panel"
                                        id="access_to_admin_panel_check"
                                    />
                                    <label class="form-check-label" for="access_to_admin_panel_check">
                                        Доступ к панели ноды
                                    </label>
                                </div>
                                <small class="form-text text-muted">
                                    Отметьте, если пользователь прошел верификацию документов или должен иметь доступ к админ-панели
                                </small>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closeUserModal">
                                Отмена
                            </button>
                            <button 
                                type="button" 
                                class="btn btn-primary" 
                                @click="saveUser"
                                :disabled="savingUser"
                            >
                                [[ savingUser ? 'Сохранение...' : 'Сохранить' ]]
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Delete Confirmation Modal -->
            <div v-if="userToDelete" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                Подтверждение удаления
                            </h5>
                            <button type="button" class="btn-close btn-close-white" @click="cancelDelete"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <p>Вы уверены, что хотите удалить пользователя?</p>
                            <div class="card">
                                <div class="card-body">
                                    <p class="mb-1"><strong>Имя:</strong> [[ userToDelete.nickname ]]</p>
                                    <p class="mb-1"><strong>Адрес:</strong> <code class="small">[[ userToDelete.wallet_address ]]</code></p>
                                    <p class="mb-0"><strong>Блокчейн:</strong> [[ userToDelete.blockchain ]]</p>
                                </div>
                            </div>
                            <div class="alert alert-warning mt-3 mb-0">
                                <i class="fas fa-exclamation-circle me-2"></i>
                                Это действие необратимо!
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="cancelDelete">
                                Отмена
                            </button>
                            <button type="button" class="btn btn-danger" @click="deleteUser">
                                <i class="fas fa-trash me-1"></i> Удалить
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Billing Modal -->
            <div v-if="showBillingModal" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-wallet me-2"></i>
                                Управление балансом
                            </h5>
                            <button type="button" class="btn-close" @click="closeBillingModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div v-if="billingUser" class="mb-3">
                                <p class="mb-1"><strong>Пользователь:</strong> [[ billingUser.nickname ]]</p>
                                <p class="mb-0"><strong>Текущий баланс:</strong> <span class="badge bg-info">[[ formatCurrency(billingUser.balance_usdt || 0) ]] USDT</span></p>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Тип операции</label>
                                <div class="btn-group w-100" role="group">
                                    <input type="radio" class="btn-check" id="billing_deposit" v-model="billingForm.isDeposit" :value="true">
                                    <label class="btn btn-outline-success" for="billing_deposit">
                                        <i class="fas fa-plus me-1"></i> Пополнить
                                    </label>
                                    
                                    <input type="radio" class="btn-check" id="billing_withdraw" v-model="billingForm.isDeposit" :value="false">
                                    <label class="btn btn-outline-danger" for="billing_withdraw">
                                        <i class="fas fa-minus me-1"></i> Списать
                                    </label>
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Сумма (USDT)</label>
                                <input 
                                    type="number" 
                                    step="0.00000001"
                                    min="0.00000001"
                                    class="form-control"
                                    v-model="billingForm.amount"
                                    placeholder="Введите сумму"
                                    :disabled="savingBilling"
                                />
                            </div>
                            
                            <div v-if="billingForm.amount && billingUser" class="alert alert-info">
                                <strong>Новый баланс:</strong> 
                                [[ formatCurrency((billingUser.balance_usdt || 0) + (billingForm.isDeposit ? parseFloat(billingForm.amount) : -parseFloat(billingForm.amount))) ]] USDT
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closeBillingModal" :disabled="savingBilling">
                                Отмена
                            </button>
                            <button 
                                type="button" 
                                class="btn" 
                                :class="billingForm.isDeposit ? 'btn-success' : 'btn-danger'"
                                @click="saveBilling"
                                :disabled="savingBilling || !billingForm.amount || parseFloat(billingForm.amount) <= 0"
                            >
                                <span v-if="savingBilling" class="spinner-border spinner-border-sm me-2"></span>
                                [[ savingBilling ? 'Обработка...' : (billingForm.isDeposit ? 'Пополнить' : 'Списать') ]]
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Billing History Modal -->
            <div v-if="showBillingHistoryModal" class="modal d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-history me-2"></i>
                                История операций
                            </h5>
                            <button 
                                type="button" 
                                class="btn btn-sm btn-outline-primary me-2" 
                                @click="loadBillingHistory"
                                :disabled="billingHistoryLoading"
                                title="Обновить"
                            >
                                <i class="fas fa-sync-alt" :class="{'fa-spin': billingHistoryLoading}"></i>
                            </button>
                            <button type="button" class="btn-close" @click="closeBillingHistoryModal"></button>
                        </div>
                        <div class="modal-body" style="padding: 2rem;">
                            <div v-if="billingHistoryUser" class="mb-3">
                                <p class="mb-1"><strong>Пользователь:</strong> [[ billingHistoryUser.nickname ]]</p>
                                <p class="mb-0"><strong>Текущий баланс:</strong> <span class="badge bg-info">[[ formatCurrency(billingHistoryUser.balance_usdt || 0) ]] USDT</span></p>
                            </div>
                            
                            <div v-if="billingHistoryLoading" class="text-center py-4">
                                <div class="spinner-border text-primary"></div>
                                <p class="mt-2">Загрузка истории...</p>
                            </div>
                            
                            <div v-else-if="billingHistory.length === 0" class="text-center py-4 text-muted">
                                <i class="fas fa-inbox fa-3x mb-3 opacity-50"></i>
                                <p>История операций пуста</p>
                            </div>
                            
                            <div v-else class="table-responsive">
                                <table class="table table-hover table-sm">
                                    <thead>
                                        <tr>
                                            <th style="width: 50px;">ID</th>
                                            <th style="width: 120px;">Тип</th>
                                            <th>Сумма</th>
                                            <th style="width: 180px;">Дата</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="transaction in billingHistory" :key="transaction.id">
                                            <td>[[ transaction.id ]]</td>
                                            <td>
                                                <span class="badge" :class="transaction.usdt_amount >= 0 ? 'bg-success' : 'bg-danger'">
                                                    <i :class="transaction.usdt_amount >= 0 ? 'fas fa-plus' : 'fas fa-minus'" class="me-1"></i>
                                                    [[ transaction.usdt_amount >= 0 ? 'Пополнение' : 'Списание' ]]
                                                </span>
                                            </td>
                                            <td>
                                                <strong :class="transaction.usdt_amount >= 0 ? 'text-success' : 'text-danger'">
                                                    [[ transaction.usdt_amount >= 0 ? '+' : '' ]][[ formatCurrency(Math.abs(transaction.usdt_amount)) ]] USDT
                                                </strong>
                                            </td>
                                            <td class="small text-muted">[[ formatDate(transaction.created_at) ]]</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            
                            <!-- Pagination -->
                            <nav v-if="getBillingHistoryTotalPages() > 1" class="mt-3">
                                <ul class="pagination justify-content-center pagination-sm">
                                    <li class="page-item" :class="{disabled: billingHistoryPage === 1}">
                                        <a class="page-link" @click.prevent="goToBillingHistoryPage(billingHistoryPage - 1)" href="#">
                                            <i class="fas fa-chevron-left"></i>
                                        </a>
                                    </li>
                                    <li class="page-item" v-for="pageNum in getBillingHistoryPaginationPages()" :key="pageNum" :class="{active: billingHistoryPage === pageNum}">
                                        <a class="page-link" @click.prevent="goToBillingHistoryPage(pageNum)" href="#">
                                            [[ pageNum ]]
                                        </a>
                                    </li>
                                    <li class="page-item" :class="{disabled: billingHistoryPage === getBillingHistoryTotalPages()}">
                                        <a class="page-link" @click.prevent="goToBillingHistoryPage(billingHistoryPage + 1)" href="#">
                                            <i class="fas fa-chevron-right"></i>
                                        </a>
                                    </li>
                                </ul>
                                <p class="text-center text-muted small mb-0">
                                    Показано [[ billingHistory.length ]] из [[ billingHistoryTotal ]] операций
                                </p>
                            </nav>
                            
                            <div v-else-if="billingHistoryTotal > 0" class="mt-2 text-center">
                                <p class="text-muted small mb-0">
                                    Всего операций: [[ billingHistoryTotal ]]
                                </p>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" @click="closeBillingHistoryModal">
                                Закрыть
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- DIDDoc Modal -->
            <did-doc-modal 
                :show="showDidDocModalFlag"
                :user-id="didDocUserId"
                :owner-info="didDocOwnerInfo"
                :use-admin-endpoint="true"
                @close="closeDidDocModal"
            ></did-doc-modal>
        </div>
    `
});

// DIDDoc Modal Component
Vue.component('DidDocModal', {
    delimiters: ['[[', ']]'],
    props: {
        show: {
            type: Boolean,
            default: false
        },
        userId: {
            type: Number,
            default: null
        },
        ownerInfo: {
            type: Object,
            default: null
        },
        useAdminEndpoint: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            isLoadingDidDoc: false,
            didDocData: null,
            didDocError: null,
            didDocOwnerInfo: null
        };
    },
    watch: {
        show(newVal) {
            if (newVal && this.userId) {
                this.loadUserDidDoc(this.userId, this.ownerInfo);
            } else if (!newVal) {
                this.closeDidDocModal();
            }
        },
        userId(newVal) {
            if (newVal && this.show) {
                this.loadUserDidDoc(newVal, this.ownerInfo);
            }
        }
    },
    methods: {
        async loadUserDidDoc(userId, ownerInfo = null) {
            if (!userId) return;
            
            this.isLoadingDidDoc = true;
            this.didDocError = null;
            this.didDocData = null;
            this.didDocOwnerInfo = ownerInfo;
            
            try {
                // Use admin endpoint if specified, otherwise use public endpoint
                const endpoint = this.useAdminEndpoint 
                    ? `/api/admin/wallet-users/${userId}/did-doc`
                    : `/api/profile/user/${userId}/did-doc`;
                
                const response = await fetch(endpoint, {
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to load DIDDoc: ${response.statusText}`);
                }
                
                this.didDocData = await response.json();
            } catch (error) {
                console.error('Error loading DIDDoc:', error);
                this.didDocError = error.message || 'Ошибка загрузки DIDDoc';
            } finally {
                this.isLoadingDidDoc = false;
            }
        },
        closeDidDocModal() {
            this.didDocData = null;
            this.didDocError = null;
            this.didDocOwnerInfo = null;
            this.$emit('close');
        },
        formatDidDoc(data) {
            if (!data) return '';
            return JSON.stringify(data, null, 2);
        },
        formatDate(dateString) {
            if (!dateString) return '';
            try {
                const date = new Date(dateString);
                return date.toLocaleString('ru-RU', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                return dateString;
            }
        },
        isTronAddress(address) {
            if (!address || typeof address !== 'string') return false;
            // TRON адреса начинаются с 'T' и имеют длину 34 символа
            return address.startsWith('T') && address.length === 34;
        },
        getTronScanUrl(address) {
            if (!address) return '#';
            return `https://tronscan.org/#/address/${address}`;
        },
        copyDidDocToClipboard() {
            if (!this.didDocData) return;
            
            const jsonString = this.formatDidDoc(this.didDocData);
            navigator.clipboard.writeText(jsonString).then(() => {
                alert('DIDDoc скопирован в буфер обмена!');
            }).catch(err => {
                console.error('Ошибка копирования:', err);
                // Fallback
                const textarea = document.createElement('textarea');
                textarea.value = jsonString;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                alert('DIDDoc скопирован в буфер обмена!');
            });
        }
    },
    template: `
        <div v-if="show" class="modal fade show" style="display: block; background-color: rgba(0, 0, 0, 0.5);" tabindex="-1" @click.self="closeDidDocModal">
            <div class="modal-dialog modal-dialog-centered modal-lg" style="max-width: 900px;">
                <div class="modal-content" style="box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15); max-height: 90vh; display: flex; flex-direction: column;">
                    <div class="modal-header bg-light">
                        <h5 class="modal-title">
                            <i class="fas fa-id-card me-2 text-primary"></i>
                            DID Document
                        </h5>
                        <button type="button" class="btn-close" @click="closeDidDocModal"></button>
                    </div>

                    <div class="modal-body" style="padding: 2rem; overflow-y: auto; flex: 1;">
                    <!-- Loading State -->
                    <div v-if="isLoadingDidDoc" class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Загрузка...</span>
                        </div>
                        <p class="mt-3 text-muted">Загрузка DIDDoc...</p>
                    </div>

                    <!-- Error State -->
                    <div v-else-if="didDocError" class="text-center py-5">
                        <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                        <p class="text-danger fw-bold mb-2">Ошибка загрузки</p>
                        <p class="text-muted">[[ didDocError ]]</p>
                    </div>

                    <!-- DIDDoc Content -->
                    <div v-else-if="didDocData">
                        <!-- Owner Info Header -->
                        <div v-if="didDocOwnerInfo || didDocData.credential" class="card mb-4 border-primary">
                            <div class="card-body">
                                <div class="d-flex align-items-center gap-3">
                                    <div class="flex-shrink-0" style="width: 80px; height: 80px;">
                                        <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center fw-bold" style="width: 80px; height: 80px; font-size: 2rem;">
                                            <img v-if="didDocOwnerInfo && didDocOwnerInfo.avatar" :src="didDocOwnerInfo.avatar" :alt="didDocOwnerInfo.nickname || 'Owner'" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                                            <span v-else>[[ ((didDocOwnerInfo && didDocOwnerInfo.nickname) || (didDocData.credential && didDocData.credential.nickname) || 'U').charAt(0).toUpperCase() ]]</span>
                                        </div>
                                    </div>
                                    <div class="flex-grow-1 min-w-0">
                                        <h4 class="mb-2 fw-bold">
                                            [[ (didDocOwnerInfo && didDocOwnerInfo.nickname) || (didDocData.credential && didDocData.credential.nickname) || 'Пользователь' ]]
                                        </h4>
                                        <a v-if="didDocData.credential && didDocData.credential.walletAddress && isTronAddress(didDocData.credential.walletAddress)" 
                                           :href="getTronScanUrl(didDocData.credential.walletAddress)" 
                                           target="_blank" 
                                           rel="noopener noreferrer"
                                           class="text-decoration-none">
                                            <code class="text-primary">[[ didDocData.credential.walletAddress ]]</code>
                                            <i class="fas fa-external-link-alt ms-1 small"></i>
                                        </a>
                                        <p v-else-if="didDocData.credential && didDocData.credential.walletAddress" class="text-muted mb-0">
                                            <code class="small">[[ didDocData.credential.walletAddress ]]</code>
                                        </p>
                                    </div>
                                    <div class="flex-shrink-0">
                                        <button 
                                            @click="copyDidDocToClipboard"
                                            class="btn btn-primary"
                                        >
                                            <i class="fas fa-copy me-2"></i>
                                            Копировать JSON
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- DID Information -->
                        <div class="card mb-4">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-info-circle text-primary me-2"></i>
                                    Основная информация
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">DID</small>
                                        <code class="small d-block" style="word-break: break-all;">[[ didDocData.id ]]</code>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Controller</small>
                                        <a v-if="isTronAddress(didDocData.controller)" 
                                           :href="getTronScanUrl(didDocData.controller)" 
                                           target="_blank" 
                                           rel="noopener noreferrer"
                                           class="text-decoration-none">
                                            <code class="text-primary small d-block" style="word-break: break-all;">[[ didDocData.controller ]]</code>
                                            <i class="fas fa-external-link-alt ms-1 small"></i>
                                        </a>
                                        <code v-else class="small d-block" style="word-break: break-all;">[[ didDocData.controller ]]</code>
                                    </div>
                                    <div v-if="didDocData.credential && didDocData.credential.blockchain" class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Blockchain</small>
                                        <span class="badge bg-info">[[ didDocData.credential.blockchain.toUpperCase() ]]</span>
                                    </div>
                                    <div v-if="didDocData.credential && didDocData.credential.ecCurve" class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">EC Curve</small>
                                        <span class="fw-bold">[[ didDocData.credential.ecCurve ]]</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Verification Proofs -->
                        <div v-if="didDocData.proof && didDocData.proof.length > 0" class="mb-4">
                            <h6 class="mb-3 fw-bold">
                                <i class="fas fa-check-circle text-success me-2"></i>
                                Доказательства и репутация
                            </h6>
                            
                            <!-- Verification Proof -->
                            <div v-for="proof in didDocData.proof" :key="proof.type" class="card mb-3">
                                <div class="card-body">
                                    <div v-if="proof.type === 'VerificationProof'">
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <h6 class="mb-0 fw-bold">
                                                <i class="fas fa-shield-alt text-primary me-2"></i>
                                                Верификация
                                            </h6>
                                            <span :class="['badge', proof.verificationStatus ? 'bg-success' : 'bg-secondary']">
                                                [[ proof.verificationStatus ? 'Проверен' : 'Не проверен' ]]
                                            </span>
                                        </div>
                                        <p v-if="proof.verifiedAt" class="text-muted small mb-0">
                                            Проверен: [[ formatDate(proof.verifiedAt) ]]
                                        </p>
                                    </div>

                                    <div v-else-if="proof.type === 'RatingProof'">
                                        <h6 class="mb-3 fw-bold">
                                            <i class="fas fa-star text-warning me-2"></i>
                                            Рейтинг и сделки
                                        </h6>
                                        <div class="row">
                                            <div class="col-4">
                                                <small class="text-muted d-block mb-1">Средний рейтинг</small>
                                                <span class="fw-bold text-warning fs-5">[[ proof.averageRating || '0.0' ]]</span>
                                            </div>
                                            <div class="col-4">
                                                <small class="text-muted d-block mb-1">Всего сделок</small>
                                                <span class="fw-bold fs-5">[[ proof.totalDeals || 0 ]]</span>
                                            </div>
                                            <div class="col-4">
                                                <small class="text-muted d-block mb-1">Транзакций</small>
                                                <span class="fw-bold fs-5">[[ proof.totalTransactions || 0 ]]</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Verification Methods -->
                        <div v-if="didDocData.verificationMethod && didDocData.verificationMethod.length > 0" class="card mb-4">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-key text-info me-2"></i>
                                    Методы верификации
                                </h6>
                            </div>
                            <div class="card-body">
                                <div v-for="(method, index) in didDocData.verificationMethod" :key="index" class="mb-3" :class="{'border-bottom pb-3': index < didDocData.verificationMethod.length - 1}">
                                    <small class="text-muted text-uppercase fw-bold d-block mb-1">ID</small>
                                    <code class="small d-block mb-3" style="word-break: break-all;">[[ method.id ]]</code>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <small class="text-muted text-uppercase fw-bold d-block mb-1">Тип</small>
                                            <span class="fw-bold">[[ method.type ]]</span>
                                        </div>
                                        <div v-if="method.blockchainAccountId" class="col-md-6">
                                            <small class="text-muted text-uppercase fw-bold d-block mb-1">Blockchain Account</small>
                                            <code class="small d-block" style="word-break: break-all;">[[ method.blockchainAccountId ]]</code>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Services -->
                        <div v-if="didDocData.service && didDocData.service.length > 0" class="card mb-4">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-server text-info me-2"></i>
                                    Сервисы
                                </h6>
                            </div>
                            <div class="card-body">
                                <div v-for="(service, index) in didDocData.service" :key="index" class="mb-3" :class="{'border-bottom pb-3': index < didDocData.service.length - 1}">
                                    <small class="text-muted text-uppercase fw-bold d-block mb-1">Тип</small>
                                    <span class="fw-bold d-block mb-2">[[ service.type ]]</span>
                                    <small class="text-muted text-uppercase fw-bold d-block mb-1">Endpoint</small>
                                    <code class="text-primary small d-block" style="word-break: break-all;">[[ service.serviceEndpoint ]]</code>
                                </div>
                            </div>
                        </div>

                        <!-- Credential Details -->
                        <div v-if="didDocData.credential" class="card mb-4">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">
                                    <i class="fas fa-user text-secondary me-2"></i>
                                    Учетные данные
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div v-if="didDocData.credential.nickname" class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Никнейм</small>
                                        <span class="fw-bold">[[ didDocData.credential.nickname ]]</span>
                                    </div>
                                    <div v-if="didDocData.credential.walletAddress" class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Адрес кошелька</small>
                                        <a v-if="isTronAddress(didDocData.credential.walletAddress)" 
                                           :href="getTronScanUrl(didDocData.credential.walletAddress)" 
                                           target="_blank" 
                                           rel="noopener noreferrer"
                                           class="text-decoration-none">
                                            <code class="text-primary small d-block" style="word-break: break-all;">[[ didDocData.credential.walletAddress ]]</code>
                                            <i class="fas fa-external-link-alt ms-1 small"></i>
                                        </a>
                                        <code v-else class="small d-block" style="word-break: break-all;">[[ didDocData.credential.walletAddress ]]</code>
                                    </div>
                                    <div v-if="didDocData.credential.createdAt" class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Создан</small>
                                        <span>[[ formatDate(didDocData.credential.createdAt) ]]</span>
                                    </div>
                                    <div v-if="didDocData.credential.updatedAt" class="col-md-6 mb-3">
                                        <small class="text-muted text-uppercase fw-bold d-block mb-1">Обновлен</small>
                                        <span>[[ formatDate(didDocData.credential.updatedAt) ]]</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" @click="closeDidDocModal">
                            Закрыть
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
});

// Deals Chat Component - Fullscreen Modal
Vue.component('DealsChat', {
    delimiters: ['[[', ']]'],
    props: {
        show: {
            type: Boolean,
            default: false
        },
        walletAddress: {
            type: String,
            default: ''
        },
        isAuthenticated: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            escrowData: {
                wallet: null,
                balance: '0',
                amount: '0',
                status: 'pending',
                guarantor: null
            }
        }
    },
    watch: {
        show(newVal) {
            if (newVal) {
                this.loadEscrowData();
            }
        }
    },
    methods: {
        close() {
            this.$emit('close');
        },
        async loadEscrowData() {
            if (!this.isAuthenticated || !this.walletAddress) {
                return;
            }
            
            try {
                // TODO: Replace with actual API call
                this.escrowData = {
                    wallet: this.walletAddress,
                    balance: '1.5',
                    amount: '0.5',
                    status: 'pending',
                    guarantor: null
                };
            } catch (error) {
                console.error('Error loading escrow data:', error);
            }
        }
    },
    template: `
        <modal-window v-if="show" :width="'90%'" :height="'100%'" @close="close">
            <template #header>
                <h3>Сделки</h3>
            </template>
            <template #body>
                <chat
                    :wallet-address="walletAddress"
                    :is-authenticated="isAuthenticated"
                >
                    <template #chat-header-addon>
                        <escrow-status-panel
                            v-if="escrowData.wallet"
                            :escrow-data="escrowData"
                        ></escrow-status-panel>
                    </template>
                </chat>
            </template>
        </modal-window>
    `
});

// Escrow Status Panel Component
Vue.component('EscrowStatusPanel', {
    delimiters: ['[[', ']]'],
    props: {
        escrowData: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            isCollapsed: false
        };
    },
    methods: {
        formatWallet(address) {
            if (!address) return '-';
            return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
        }
    },
    template: `
        <div class="bg-light border-bottom px-4 py-3" style="flex-shrink: 0;">
            <div class="d-flex align-items-center justify-content-between" style="cursor: pointer;" @click="isCollapsed = !isCollapsed">
                <div class="d-flex align-items-center" style="gap: 8px;">
                    <span style="font-size: 18px;">💼</span>
                    <span class="fw-semibold">Статус эскроу</span>
                </div>
                <svg 
                    style="width: 20px; height: 20px; color: #6b7280; transition: transform 0.3s;"
                    :style="{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
            </div>
            <div v-show="!isCollapsed" class="mt-3" style="display: flex; flex-direction: column; gap: 8px; font-size: 14px;">
                <div class="d-flex justify-content-between">
                    <span class="text-muted">Кошелек эскроу:</span>
                    <span class="font-monospace fw-semibold">[[ formatWallet(escrowData.wallet) ]]</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted">Баланс:</span>
                    <span class="fw-semibold">[[ escrowData.balance ]] USDT</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted">Сумма:</span>
                    <span class="fw-semibold">[[ escrowData.amount ]] USDT</span>
                </div>
                <div v-if="escrowData.guarantor" class="d-flex justify-content-between">
                    <span class="text-muted">Гарант:</span>
                    <span class="font-monospace fw-semibold">[[ formatWallet(escrowData.guarantor) ]]</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted">Статус:</span>
                    <span :class="[
                        'badge',
                        escrowData.status === 'success' ? 'bg-success' :
                        escrowData.status === 'rejected' ? 'bg-danger' :
                        'bg-warning'
                    ]" style="text-transform: uppercase; font-size: 11px;">
                        [[ escrowData.status === 'success' ? 'Успешно' : escrowData.status === 'rejected' ? 'Отклонено' : 'В ожидании' ]]
                    </span>
                </div>
            </div>
        </div>
    `
});

// TRON Transaction Signing Component (Universal)
// Универсальный компонент для подписи любых TRON транзакций
Vue.component('TronSign', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            // Wallet state
            walletAddress: null,
            isConnected: false,
            isConnecting: false,
            isSigning: false,
            isMobileDevice: false
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
        this.checkTronWeb();
    },
    
    methods: {
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
         * Проверка наличия TronLink и автоматическое подключение, если кошелек уже разблокирован
         */
        async checkTronWeb() {
            // Wait for TronLink injection
            let attempts = 0;
            const maxWaitAttempts = 30;
            
            while (attempts < maxWaitAttempts) {
                if (typeof window.tronWeb !== 'undefined') {
                    break;
                }
                await new Promise(resolve => setTimeout(resolve, 100));
                attempts++;
            }
            
            if (typeof window.tronWeb === 'undefined') {
                return;
            }
            
            // Check if wallet is connected
            const isLocked = !window.tronWeb.ready || 
                            !window.tronWeb.defaultAddress || 
                            window.tronWeb.defaultAddress.base58 === false;
            
            if (!isLocked) {
                this.walletAddress = window.tronWeb.defaultAddress.base58;
                this.isConnected = true;
                this.$emit('connected', { address: this.walletAddress });
            }
        },
        
        /**
         * Подключение кошелька TronLink
         */
        async connectWallet() {
            this.isConnecting = true;
            
            try {
                // Wait for TronLink injection
                let attempts = 0;
                const maxWaitAttempts = 30;
                
                while (attempts < maxWaitAttempts) {
                    if (typeof window.tronWeb !== 'undefined') {
                        break;
                    }
                    await new Promise(resolve => setTimeout(resolve, 100));
                    attempts++;
                }
                
                if (typeof window.tronWeb === 'undefined') {
                    const error = 'TronLink не установлен. Установите расширение TronLink.';
                    this.$emit('error', { message: error, type: 'connection' });
                    throw new Error(error);
                }
                
                // Check if wallet is locked
                const isLocked = !window.tronWeb.ready || 
                                !window.tronWeb.defaultAddress || 
                                window.tronWeb.defaultAddress.base58 === false;
                
                if (isLocked) {
                    // Request access
                    if (window.tronLink) {
                        try {
                            const requestParams = { 
                                method: 'tron_requestAccounts' 
                            };
                            
                            // Для TrustWallet на мобильных устройствах добавляем версию DApp
                            if (this.isMobileDevice) {
                                requestParams.dappVersion = '1.0.0';
                            }
                            
                            await window.tronLink.request(requestParams);
                        } catch (e) {
                            if (e.code === 4001) {
                                const error = 'Вы отклонили запрос на подключение';
                                this.$emit('error', { message: error, type: 'connection' });
                                throw new Error(error);
                            }
                        }
                    }
                }
                
                // Wait for ready
                attempts = 0;
                const maxReadyAttempts = 50;
                
                while (attempts < maxReadyAttempts) {
                    if (window.tronWeb && 
                        window.tronWeb.ready && 
                        window.tronWeb.defaultAddress &&
                        window.tronWeb.defaultAddress.base58 &&
                        window.tronWeb.defaultAddress.base58 !== false) {
                        
                        this.walletAddress = window.tronWeb.defaultAddress.base58;
                        this.isConnected = true;
                        this.$emit('connected', { address: this.walletAddress });
                        return;
                    }
                    
                    await new Promise(resolve => setTimeout(resolve, 100));
                    attempts++;
                }
                
                const error = 'TronLink не готов. Разблокируйте кошелек и попробуйте снова.';
                this.$emit('error', { message: error, type: 'connection' });
                throw new Error(error);
                
            } catch (error) {
                const errorMessage = this.extractErrorMessage(error);
                this.$emit('error', { message: errorMessage, type: 'connection' });
                throw error;
            } finally {
                this.isConnecting = false;
            }
        },
        
        /**
         * Отключение кошелька
         */
        disconnect() {
            this.walletAddress = null;
            this.isConnected = false;
            this.$emit('disconnected', {});
        },
        
        /**
         * Валидация формата транзакции TRON
         * Выводит детальную диагностику в консоль при ошибках
         */
        validateTransactionFormat(transaction) {
            console.group('🔍 TronSign: Валидация формата транзакции');
            
            // Проверка наличия transaction
            if (!transaction) {
                console.error('❌ Транзакция не передана (null/undefined)');
                console.groupEnd();
                return false;
            }
            
            // Проверка типа
            if (typeof transaction !== 'object') {
                console.error('❌ Транзакция должна быть объектом, получен:', typeof transaction);
                console.groupEnd();
                return false;
            }
            
            // Извлечение транзакции, если обернута в "transaction"
            let tx = transaction;
            if (transaction.transaction && typeof transaction.transaction === 'object') {
                console.log('⚠️ Транзакция обернута в ключ "transaction", извлекаем...');
                tx = transaction.transaction;
            }
            
            // Проверка raw_data
            if (!tx.raw_data) {
                console.error('❌ Транзакция не содержит raw_data');
                console.log('Ключи транзакции:', Object.keys(tx));
                console.groupEnd();
                return false;
            }
            
            // Проверка contract
            if (!tx.raw_data.contract || !Array.isArray(tx.raw_data.contract)) {
                console.error('❌ Транзакция не содержит contract в raw_data');
                console.log('raw_data ключи:', Object.keys(tx.raw_data));
                console.groupEnd();
                return false;
            }
            
            // Успешная валидация
            console.log('✅ Формат транзакции корректен');
            console.log('TX ID:', tx.txID);
            console.log('Contract type:', tx.raw_data.contract[0]?.type);
            console.log('Contract count:', tx.raw_data.contract.length);
            console.groupEnd();
            return true;
        },
        
        /**
         * Извлечение сообщения об ошибке из разных форматов
         */
        extractErrorMessage(error) {
            if (!error) {
                return 'Неизвестная ошибка';
            }
            
            if (typeof error === 'string') {
                return error;
            }
            
            if (error.message) {
                return error.message;
            }
            
            if (error.error) {
                return error.error;
            }
            
            if (error.toString && error.toString() !== '[object Object]') {
                return error.toString();
            }
            
            return 'Неизвестная ошибка';
        },
        
        /**
         * Подпись транзакции через TronLink
         * @param {Object} unsignedTransaction - Неподписанная транзакция TRON
         * @returns {Promise<Object>} Подписанная транзакция
         */
        async signTransaction(unsignedTransaction) {
            // Валидация подключения
            if (!this.isConnected) {
                const error = 'Кошелек не подключен. Вызовите connectWallet() сначала.';
                console.error('❌ TronSign:', error);
                this.$emit('error', { message: error, type: 'connection' });
                throw new Error(error);
            }
            
            // Валидация формата
            if (!this.validateTransactionFormat(unsignedTransaction)) {
                const error = 'Неверный формат транзакции. Проверьте консоль для деталей.';
                this.$emit('error', { message: error, type: 'validation' });
                throw new Error(error);
            }
            
            // Извлечение транзакции
            let transactionToSign = unsignedTransaction;
            if (unsignedTransaction.transaction && typeof unsignedTransaction.transaction === 'object') {
                transactionToSign = unsignedTransaction.transaction;
            }
            
            // Эмит события signing
            this.$emit('signing', { txId: transactionToSign.txID });
            this.isSigning = true;
            
            try {
                // Подпись через TronLink
                const signedTx = await window.tronWeb.trx.sign(transactionToSign);
                
                // Проверка подписи
                if (!signedTx || !signedTx.signature) {
                    throw new Error('Ошибка подписи транзакции: подпись не получена');
                }
                
                // Эмит события signed
                const txId = signedTx.txID || transactionToSign.txID;
                this.$emit('signed', {
                    signedTransaction: signedTx,
                    txId: txId
                });
                
                return signedTx;
                
            } catch (error) {
                // Обработка ошибок подписи
                let errorMessage = this.extractErrorMessage(error);
                
                // Проверяем типичные ошибки TronLink
                const errorStr = errorMessage.toLowerCase();
                if (errorStr.includes('declined') || errorStr.includes('rejected') || errorStr.includes('отклонен')) {
                    errorMessage = 'Подпись транзакции отклонена пользователем';
                } else if (errorStr.includes('cancelled') || errorStr.includes('canceled')) {
                    errorMessage = 'Подпись транзакции отменена';
                } else if (errorStr.includes('timeout')) {
                    errorMessage = 'Время ожидания подписи истекло';
                } else if (errorStr.includes('locked') || errorStr.includes('not ready')) {
                    errorMessage = 'Кошелек заблокирован. Разблокируйте TronLink и попробуйте снова';
                }
                
                console.error('❌ TronSign: Ошибка подписи:', errorMessage);
                
                this.$emit('error', {
                    message: errorMessage,
                    type: 'signing'
                });
                
                throw new Error(errorMessage);
            } finally {
                this.isSigning = false;
            }
        }
    },
    
    template: `<div></div>`
});

// Deal Conversation Component - Singleton wrapper for Chat with backend integration
Vue.component('DealConversation', {
    delimiters: ['[[', ']]'],
    props: {
        show: {
            type: Boolean,
            default: false
        },
        walletAddress: {
            type: String,
            default: ''
        },
        isAuthenticated: {
            type: Boolean,
            default: false
        },
        dealId: {
            type: [String, Number],
            default: null
        },
        currentUserDid: {
            type: String,
            default: null
        }
    },
    data() {
        return {
            chatVisible: false,
            sessionsLoaded: false,
            userDid: null
        }
    },
    watch: {
        show(newVal) {
            this.chatVisible = newVal;
        },
        isAuthenticated(newVal) {
            if (newVal && !this.sessionsLoaded) {
                this.loadLastSessions();
            }
        },
        currentUserDid(newVal) {
            this.userDid = newVal;
        }
    },
    async mounted() {
        // Load user DID from profile if authenticated
        if (this.isAuthenticated) {
            await this.loadUserDid();
            if (this.userDid) {
                await this.loadLastSessions();
            }
        }
    },
    methods: {
        async loadUserDid() {
            try {
                const token = this.getAuthToken();
                if (!token) return;
                
                const response = await fetch('/api/profile/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    const profile = await response.json();
                    this.userDid = profile.did || null;
                }
            } catch (error) {
                console.error('Error loading user DID:', error);
            }
        },
        
        getAuthToken() {
            const cookies = document.cookie.split(';');
            const tokenCookie = cookies.find(c => c.trim().startsWith('tron_auth_token='));
            if (tokenCookie) {
                return tokenCookie.split('=')[1];
            }
            // Fallback to localStorage
            return localStorage.getItem('access_token');
        },
        
        async loadLastSessions() {
            if (this.sessionsLoaded || !this.isAuthenticated || !this.userDid) {
                return;
            }
            
            try {
                const token = this.getAuthToken();
                if (!token) return;
                
                const response = await fetch('/chat/api/sessions?limit=50', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.sessionsLoaded = true;
                    
                    // Add contacts from sessions to chat component
                    this.$nextTick(() => {
                        if (this.$refs.chatComponent && result.sessions) {
                            result.sessions.forEach(session => {
                                const conversationId = session.conversation_id;
                                const lastMessage = session.last_message;
                                
                                // Check if contact already exists
                                const existingContact = this.$refs.chatComponent.contacts.find(
                                    c => c.id === conversationId
                                );
                                
                                if (!existingContact && lastMessage) {
                                    // Create contact from session
                                    const contactName = lastMessage.sender_id === this.userDid 
                                        ? (lastMessage.receiver_id || 'Contact')
                                        : (lastMessage.sender_id || 'Contact');
                                    
                                    this.$refs.chatComponent.contacts.push({
                                        id: conversationId,
                                        name: contactName.substring(0, 20) + (contactName.length > 20 ? '...' : ''),
                                        avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${conversationId}`,
                                        status: 'online',
                                        lastMessage: lastMessage.text || '',
                                        did: conversationId,
                                        isTyping: false
                                    });
                                }
                            });
                        }
                    });
                }
            } catch (error) {
                console.error('Error loading last sessions:', error);
            }
        },
        
        async openChatWithOwner(ownerDid, ownerInfo = {}) {
            if (!this.isAuthenticated || !this.userDid) {
                console.warn('User not authenticated or DID not available');
                return;
            }
            
            if (!ownerDid) {
                console.warn('Owner DID not provided');
                return;
            }
            
            // Ensure chat component is ready
            this.$nextTick(() => {
                if (!this.$refs.chatComponent) {
                    console.error('Chat component not ready');
                    return;
                }
                
                const chat = this.$refs.chatComponent;
                
                // Check if contact already exists
                let contact = chat.contacts.find(c => c.id === ownerDid);
                
                if (!contact) {
                    // Create new contact
                    contact = {
                        id: ownerDid,
                        name: ownerInfo.nickname || ownerDid.substring(0, 20) + (ownerDid.length > 20 ? '...' : ''),
                        avatar: ownerInfo.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${ownerDid}`,
                        status: 'online',
                        lastMessage: '',
                        did: ownerDid,
                        isTyping: false
                    };
                    chat.contacts.push(contact);
                }
                
                // Select contact and open chat
                chat.selectContact(contact);
                this.chatVisible = true;
                
                // Load chat history for this contact
                this.loadChatHistory(ownerDid);
            });
        },
        
        async loadChatHistory(conversationId) {
            if (!this.isAuthenticated || !this.userDid) {
                return;
            }
            
            try {
                const token = this.getAuthToken();
                if (!token) return;
                
                const response = await fetch(
                    `/chat/api/history?conversation_id=${encodeURIComponent(conversationId)}&page=1&page_size=20`,
                    {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    }
                );
                
                if (response.ok) {
                    const result = await response.json();
                    
                    if (result.messages && result.messages.length > 0) {
                        this.$nextTick(() => {
                            if (this.$refs.chatComponent) {
                                this.$refs.chatComponent.set_history(result.messages);
                            }
                        });
                    }
                }
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        },
        
        close() {
            this.chatVisible = false;
            this.$emit('close');
        },
        
        async handleSendTextMessage(event) {
            if (!this.isAuthenticated || !this.userDid) {
                console.warn('User not authenticated or DID not available');
                return;
            }
            
            try {
                const messageData = {
                    uuid: event.messageUuid,
                    message_type: 'text',
                    sender_id: this.userDid,
                    receiver_id: event.contactId,
                    text: event.text,
                    attachments: null
                };
                
                const token = this.getAuthToken();
                const response = await fetch('/chat/api/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        message: messageData,
                        deal_uid: null
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    console.error('Failed to send text message:', error);
                }
            } catch (error) {
                console.error('Error sending text message:', error);
            }
        },
        
        async handleSendDocuments(event) {
            if (!this.isAuthenticated || !this.userDid) {
                console.warn('User not authenticated or DID not available');
                return;
            }
            
            try {
                const apiAttachments = event.attachments.map(att => ({
                    id: att.id,
                    type: att.type,
                    name: att.name,
                    size: att.size,
                    mime_type: att.mime_type,
                    data: att.data
                }));
                
                const messageType = event.text ? 'mixed' : 'file';
                
                const messageData = {
                    uuid: event.messageUuid,
                    message_type: messageType,
                    sender_id: this.userDid,
                    receiver_id: event.contactId,
                    text: event.text || null,
                    attachments: apiAttachments
                };
                
                const token = this.getAuthToken();
                const response = await fetch('/chat/api/messages', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        message: messageData,
                        deal_uid: null
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    console.error('Failed to send message with attachments:', error);
                }
            } catch (error) {
                console.error('Error sending message with attachments:', error);
            }
        },
        
        async handleSign(event) {
            if (!this.isAuthenticated) {
                alert('Please authenticate first');
                return;
            }
            
            if (typeof window.tronWeb === 'undefined') {
                alert('TronLink is not installed');
                return;
            }
            
            try {
                const tronWeb = window.tronWeb;
                const message = event.text;
                
                const signature = await tronWeb.trx.sign(message);
                
                if (this.$refs.chatComponent) {
                    this.$refs.chatComponent.onSignatureResult(event.messageUuid, signature);
                }
            } catch (error) {
                console.error('Error signing message:', error);
                alert('Error signing message: ' + error.message);
            }
        },
        
        handleAudio(event) {
            console.log('DealConversation: on_audio', event);
        },
        
        handleVideo(event) {
            console.log('DealConversation: on_video', event);
        },
        
        async handleLoadAttachment(event) {
            try {
                const token = this.getAuthToken();
                const headers = {
                    'Content-Type': 'application/json'
                };
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }
                
                const response = await fetch(`/chat/api/attachment/${event.messageUuid}/${event.attachmentId}`, {
                    method: 'GET',
                    headers: headers
                });
                
                if (!response.ok) {
                    throw new Error('Failed to fetch attachment');
                }
                
                const attachmentData = await response.json();
                event.resolve(attachmentData);
            } catch (error) {
                console.error('Error fetching attachment:', error);
                event.reject(error);
            }
        },
        
        async handleRefreshHistory(event) {
            if (!this.isAuthenticated || !this.userDid) {
                event.reject(new Error('User not authenticated'));
                return;
            }
            
            try {
                const token = this.getAuthToken();
                const conversationId = event.conversation_id;
                const afterMessageUid = event.last_message_uid;
                
                const url = `/chat/api/history?conversation_id=${encodeURIComponent(conversationId)}&page=1&page_size=20&after_message_uid=${encodeURIComponent(afterMessageUid)}`;
                
                const response = await fetch(url, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (!response.ok) {
                    if (response.status === 404) {
                        event.resolve([]);
                        return;
                    }
                    throw new Error(`Failed to refresh history: ${response.statusText}`);
                }
                
                const result = await response.json();
                event.resolve(result.messages || []);
            } catch (error) {
                console.error('Error refreshing history:', error);
                event.reject(error);
            }
        },
        
        async handleFetchHistory(event) {
            if (!this.isAuthenticated || !this.userDid) {
                event.reject(new Error('User not authenticated'));
                return;
            }
            
            try {
                const token = this.getAuthToken();
                const conversationId = event.conversation_id;
                const beforeMessageUid = event.before_message_uid;
                const pageSize = this.$refs.chatComponent?.pageSize || 20;
                
                const url = `/chat/api/history?conversation_id=${encodeURIComponent(conversationId)}&page=1&page_size=${pageSize}&before_message_uid=${encodeURIComponent(beforeMessageUid)}`;
                
                const response = await fetch(url, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (!response.ok) {
                    if (response.status === 404) {
                        event.resolve([]);
                        return;
                    }
                    throw new Error(`Failed to fetch history: ${response.statusText}`);
                }
                
                const result = await response.json();
                event.resolve(result.messages || []);
            } catch (error) {
                console.error('Error fetching history:', error);
                event.reject(error);
            }
        }
    },
    template: `
        <div>
            <chat
                ref="chatComponent"
                :show="chatVisible"
                :wallet-address="walletAddress"
                :is-authenticated="isAuthenticated"
                :current-user-did="userDid || currentUserDid"
                @close="close"
                @on_send_text_message="handleSendTextMessage"
                @on_send_documents="handleSendDocuments"
                @on_sign="handleSign"
                @on_audio="handleAudio"
                @on_video="handleVideo"
                @on_load_attachment="handleLoadAttachment"
                @on_download_attachment="handleLoadAttachment"
                @on_refresh_history="handleRefreshHistory"
                @on_fetch_history="handleFetchHistory"
            ></chat>
        </div>
    `
});

// Arbiter Component
Vue.component('Arbiter', {
    delimiters: ['[[', ']]'],
    data() {
        return {
            isInitialized: false,
            loading: true,
            error: null
        };
    },
    mounted() {
        this.checkInitialization();
    },
    methods: {
        async checkInitialization() {
            this.loading = true;
            this.error = null;
            try {
                const response = await fetch('/api/marketplace/arbiter/is-initialized');
                if (!response.ok) {
                    throw new Error('Ошибка проверки инициализации арбитра');
                }
                const data = await response.json();
                this.isInitialized = data.initialized || false;
            } catch (error) {
                console.error('Error checking arbiter initialization:', error);
                this.error = error.message || 'Ошибка проверки инициализации';
            } finally {
                this.loading = false;
            }
        }
    },
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fas fa-gavel me-1"></i>
                Арбитр
            </div>
            <div class="card-body">
                <div v-if="loading" class="text-center py-3">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                </div>
                <div v-else-if="error" class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    [[ error ]]
                </div>
                <div v-else-if="!isInitialized" class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Внимание!</strong> Кошелек арбитра не инициализирован. 
                    Пожалуйста, инициализируйте кошелек арбитра для работы с арбитражем.
                </div>
                <div v-else class="text-center py-5">
                    <h3 class="text-muted">Арбитр</h3>
                    <p class="text-muted">Раздел находится в разработке</p>
                </div>
            </div>
        </div>
    `
});