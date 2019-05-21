import Vue from 'vue';
import './plugins/vuetify';
import App from './App.vue';
import router from './router';
import store from './store';
import './registerServiceWorker';
import { Rpc } from '@/plugins/rpc';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'font-awesome/css/font-awesome.css';

Vue.config.productionTip = false;

Vue.use(Rpc);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
