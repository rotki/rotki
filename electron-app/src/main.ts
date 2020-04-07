import Vue from 'vue';
import App from '@/App.vue';
import '@/filters';
import { Api } from '@/plugins/api';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'font-awesome/css/font-awesome.css';
import { Interop } from '@/plugins/interop';
import vuetify from '@/plugins/vuetify';
import { setupPremium } from '@/utils/premium';
import router from './router';
import store from './store/store';

Vue.config.productionTip = false;

Vue.use(Api);
Vue.use(Interop);

setupPremium();

new Vue({
  vuetify,
  router,
  store,
  render: h => h(App)
}).$mount('#app');
