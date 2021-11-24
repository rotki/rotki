/* istanbul ignore file */

import _Vue from 'vue';
import { api, RotkehlchenApi } from '@/services/rotkehlchen-api';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Api(vue: typeof _Vue, options?: any): void {
  vue.prototype.$api = api;
}

declare module 'vue/types/vue' {
  interface Vue {
    $api: RotkehlchenApi;
  }
}
