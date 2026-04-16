import { createPinia } from 'pinia';
import { StoreResetPlugin } from '@/modules/app/store-plugins';

export function createCustomPinia() {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
}
