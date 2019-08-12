import Vue from 'vue';
import App from './App.vue';
import router from './router';
import store from './store/store';
import './registerServiceWorker';
import './filters';
import { Rpc } from '@/plugins/rpc';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'font-awesome/css/font-awesome.css';
import vuetify from '@/plugins/vuetify';

Vue.config.productionTip = false;

Vue.use(Rpc);

new Vue({
  vuetify,
  router,
  store,
  render: h => h(App)
}).$mount('#app');
