import { createPinia } from 'pinia';

const createCustomPinia = () => {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);

  return pinia;
};

export default createCustomPinia;
