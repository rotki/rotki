import _Vue from 'vue';
import { api, RotkehlchenApi } from '@/services/rotkehlchen-api';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Api(Vue: typeof _Vue, options?: any): void {
  Vue.prototype.$api = api;
}

declare module 'vue/types/vue' {
  interface Vue {
    $api: RotkehlchenApi;
  }
}
