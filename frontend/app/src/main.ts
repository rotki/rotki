/* istanbul ignore file */

import VueCompositionAPI, { provide } from '@vue/composition-api';
import { createPinia, PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import App from '@/App.vue';
import '@/filters';
import '@/main.scss';
import { Api } from '@/plugins/api';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'typeface-roboto-mono';
import './register-sw';
import { Interop } from '@/plugins/interop';
import vuetify from '@/plugins/vuetify';
import { setupPremium } from '@/premium/setup-interface';
import { setupDayjs } from '@/utils/date';
import { setupFormatter } from '@/utils/setup-formatter';
import i18n from './i18n';
import router from './router';
import store from './store/store';
import './utils/logging';

Vue.config.productionTip = false;

Vue.use(Api);
Vue.use(Interop);
Vue.use(VueCompositionAPI);
Vue.use(PiniaVuePlugin);

setupPremium();

Vue.directive('blur', {
  inserted: function (el) {
    el.onfocus = ({ target }) => {
      if (!target) {
        return;
      }
      (target as any).blur();
    };
  }
});

const pinia = createPinia();

new Vue({
  setup() {
    provide('vuex-store', store);
  },
  vuetify,
  router,
  store,
  pinia,
  i18n,
  render: h => h(App)
}).$mount('#app');

setupDayjs();
setupFormatter();
