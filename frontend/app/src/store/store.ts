import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { balances } from '@/store/balances';
import { storeVuexPlugins } from '@/store/debug';
import { RotkehlchenState } from '@/store/types';

Vue.use(Vuex);

const store: StoreOptions<RotkehlchenState> = {
  modules: {
    balances
  },
  plugins: storeVuexPlugins()
};
export default new Vuex.Store(store);
