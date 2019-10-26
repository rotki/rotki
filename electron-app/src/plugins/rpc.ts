import _Vue from 'vue';
import { RotkehlchenService } from '@/services/rotkehlchen_service';

export function Rpc(Vue: typeof _Vue, options?: any): void {
  Vue.prototype.$rpc = new RotkehlchenService();
}

declare module 'vue/types/vue' {
  interface Vue {
    $rpc: RotkehlchenService;
  }
}
