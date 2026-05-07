import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import DbAdmin from './DbAdmin.vue'

const app = createApp(DbAdmin)
app.use(ElementPlus, { locale: zhCn })
app.mount('#dbadmin-app')
