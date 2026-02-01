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
    template: `
        <div class="card mb-4">
            <div class="card-header">
                <i class="fa-regular fa-address-card me-1"></i>
                Профиль
            </div>
            <div class="card-body">
                <p>Страница профиля пользователя.</p>
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