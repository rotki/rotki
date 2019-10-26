import Vue from 'vue';
import App from './App.vue';
import router from './router';
import store from './store';
import './registerServiceWorker';
import { Rpc } from '@/plugins/rpc';

Vue.config.productionTip = false;

Vue.use(Rpc);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
