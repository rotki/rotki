import { createPinia } from 'pinia';
import { StoreResetPlugin } from '@/store/plugins';

const createCustomPinia = () => {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
};

export default createCustomPinia;
