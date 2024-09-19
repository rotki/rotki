/* istanbul ignore file */
import { createPinia } from 'pinia';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'typeface-roboto-mono';
import 'flag-icons/css/flag-icons.min.css';
import { usePremiumApi } from '@/premium/setup-interface';
import App from '@/App.vue';
import { attemptPolyfillResizeObserver } from '@/utils/cypress';
import { registerDevtools } from '@/plugins/devtools';
import { i18n } from './i18n';
import { router } from './router';
import { createRuiPlugin } from './plugins/rui';
import '@/main.scss';

const isDevelopment = checkIfDevelopment() && !import.meta.env.VITE_TEST;
const IS_CLIENT = typeof window !== 'undefined';

attemptPolyfillResizeObserver();

const pinia = createPinia();
pinia.use(StoreResetPlugin);
pinia.use(StoreTrackPlugin);

if (isDevelopment)
  pinia.use(StoreStatePersistsPlugin);

setActivePinia(pinia);

const itemsPerPage = useItemsPerPage();

const rui = createRuiPlugin({
  table: { itemsPerPage, globalItemsPerPage: true, limits: [10, 25, 50, 100], stickyOffset: 60 },
});

const app = createApp(App);

app.directive('blur', {
  mounted(el): void {
    el.addEventListener('focus', (event: any): void => {
      if (!event.target)
        return;

      event.target.blur();
    });
  },
});

app.provide('premium', usePremiumApi());

app.use(rui);
app.use(pinia);
app.use(i18n);
app.use(router);
app.mount('#app');

setupDayjs();
setupFormatter();

if (isDevelopment && IS_CLIENT)
  registerDevtools(app);

export { app };
