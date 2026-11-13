import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { bootstrapLegacyAuth } from './utils/authStorage'

bootstrapLegacyAuth()

const app = createApp(App)

app.use(router)

app.mount('#app')
