import { StoreResetPlugin } from '@/store/plugins';
import { createPinia } from 'pinia';

export function createCustomPinia() {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
}
