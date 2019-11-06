import _Vue from 'vue';
import { RotkehlchenService } from '@/services/rotkehlchen_service';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Rpc(Vue: typeof _Vue, options?: any): void {
  Vue.prototype.$rpc = new RotkehlchenService();
}

declare module 'vue/types/vue' {
  interface Vue {
    $rpc: RotkehlchenService;
  }
}
