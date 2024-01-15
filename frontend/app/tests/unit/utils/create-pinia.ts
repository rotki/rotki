import { createPinia } from 'pinia';

function createCustomPinia() {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
}

export default createCustomPinia;
