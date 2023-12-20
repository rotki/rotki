/* istanbul ignore file */
import { PiniaVuePlugin, createPinia } from 'pinia';
import Vue, { provide } from 'vue';
import App from '@/App.vue';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'typeface-roboto-mono';
import { vuetify } from '@/plugins/vuetify';
import { usePremiumApi } from '@/premium/setup-interface';
import i18n from './i18n';
import router from './router';
import rui from './plugins/rui';

import '@/plugins/rui';
import '@/main.scss';

const isDevelopment = checkIfDevelopment() && !import.meta.env.VITE_TEST;
Vue.config.productionTip = false;
Vue.config.devtools = isDevelopment;

Vue.use(PiniaVuePlugin);
Vue.use(i18n);
Vue.use(rui);

// This should disable vite page reloads on CI.
// Monitor e2e tests for this and if this doesn't work remove it.
if (import.meta.env.MODE === 'production' && import.meta.env.VITE_TEST) {
  logger.info('disabling vite:reload');
  if (import.meta.hot) {
    import.meta.hot.on('vite:beforeFullReload', () => {
      logger.info('vite:reload detected');
      throw new Error('(skipping full reload)');
    });
  }
}

Vue.directive('blur', {
  inserted(el) {
    el.addEventListener('focus', ({ target }): void => {
      if (!target) {
        return;
      }
      (target as any).blur();
    });
  }
});

const pinia = createPinia();
pinia.use(StoreResetPlugin);
pinia.use(StoreTrackPlugin);

if (isDevelopment) {
  pinia.use(storePiniaPlugins);
}
setActivePinia(pinia);

new Vue({
  setup(): void {
    provide('premium', usePremiumApi());
    rui.setupProvide();
  },
  vuetify,
  router,
  pinia,
  i18n,
  render: h => h(App)
}).$mount('#app');

setupDayjs();
setupFormatter();
