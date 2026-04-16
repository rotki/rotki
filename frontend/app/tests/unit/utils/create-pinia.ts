import { createPinia } from 'pinia';
import { StoreResetPlugin } from '@/modules/shell/app/store-plugins';

export function createCustomPinia() {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
}
