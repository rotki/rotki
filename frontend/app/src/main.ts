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
import { Interop } from '@/plugins/interop';
import vuetify from '@/plugins/vuetify';
import { usePremiumApi } from '@/premium/setup-interface';
import { storePiniaPlugins } from '@/store/debug';
import { setupDayjs } from '@/utils/date';
import { checkIfDevelopment } from '@/utils/env-utils';
import { setupFormatter } from '@/utils/setup-formatter';
import i18n from './i18n';
import router from './router';
import './utils/logging';

Vue.config.productionTip = false;
Vue.config.devtools = checkIfDevelopment() && !import.meta.env.VITE_TEST;

Vue.use(Api);
Vue.use(Interop);
Vue.use(VueCompositionAPI);
Vue.use(PiniaVuePlugin);

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
pinia.use(storePiniaPlugins);

new Vue({
  setup() {
    provide('premium', usePremiumApi());
  },
  vuetify,
  router,
  pinia,
  i18n,
  render: h => h(App)
}).$mount('#app');

setupDayjs();
setupFormatter();
