import { createLocalVue } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import Vuex from 'vuex';
import store from '@/store/store';
import { I18n } from '../i18n';

export const mountOptions = () => {
  const vuetify = new Vuetify();
  const pinia = createPinia();
  setActivePinia(pinia);
  const localVue = createLocalVue();
  localVue.use(I18n);
  localVue.use(Vuetify);
  localVue.use(Vuex);

  return {
    localVue,
    store,
    pinia,
    provide: {
      'vuex-store': store
    },
    vuetify
  };
};
