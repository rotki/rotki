/* istanbul ignore file */
import { createPinia } from 'pinia';
import { checkIfDevelopment } from '@shared/utils';
import { setupFormatter } from '@/utils/setup-formatter';
import { setupDayjs } from '@/utils/date';
import { usePremiumApi } from '@/premium/setup-interface';
import App from '@/App.vue';
import { attemptPolyfillResizeObserver } from '@/utils/cypress';
import { registerDevtools } from '@/plugins/devtools';
import { i18n } from '@/i18n';
import { router } from '@/router';
import { createRuiPlugin } from '@/plugins/rui';
import { StoreResetPlugin, StoreTrackPlugin } from '@/store/plugins';
import { StoreStatePersistsPlugin } from '@/store/debug';
import { useItemsPerPage } from '@/composables/session/use-items-per-page';
import './main.scss';
import 'roboto-fontface/css/roboto/roboto-fontface.css';
import 'typeface-roboto-mono';
import 'flag-icons/css/flag-icons.min.css';

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
const { isMdAndDown } = useBreakpoint();

const rui = createRuiPlugin({
  table: { globalItemsPerPage: true, itemsPerPage, limits: [10, 25, 50, 100], stickyOffset: computed(() => get(isMdAndDown) ? 56 : 64) },
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
