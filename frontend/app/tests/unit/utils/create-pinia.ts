import { createPinia } from 'pinia';
import { StoreResetPlugin } from '@/store/plugins';

export function createCustomPinia() {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
}
