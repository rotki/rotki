/* istanbul ignore file */

import { createPinia, PiniaVuePlugin } from 'pinia';
import Vue, { provide } from 'vue';
import App from '@/App.vue';
import '@/filters';
import '@/main.scss';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'typeface-roboto-mono';
import vuetify from '@/plugins/vuetify';
import { usePremiumApi } from '@/premium/setup-interface';
import { storePiniaPlugins } from '@/store/debug';
import { StoreResetPlugin, StoreTrackPlugin } from '@/store/plugins';
import { setupDayjs } from '@/utils/date';
import { checkIfDevelopment } from '@/utils/env-utils';
import { setupFormatter } from '@/utils/setup-formatter';
import i18n from './i18n';
import router from './router';
import './utils/logging';

const isDevelopment = checkIfDevelopment() && !import.meta.env.VITE_TEST;
Vue.config.productionTip = false;
Vue.config.devtools = isDevelopment;

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
pinia.use(StoreResetPlugin);
pinia.use(StoreTrackPlugin);

if (isDevelopment) {
  pinia.use(storePiniaPlugins);
}

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
