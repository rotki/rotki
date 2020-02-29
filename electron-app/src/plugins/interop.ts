import _Vue from 'vue';
import { ElectronInterop, interop } from '@/electron-interop';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Interop(Vue: typeof _Vue, options?: any): void {
  Vue.prototype.$interop = interop;
}

declare module 'vue/types/vue' {
  interface Vue {
    $interop: ElectronInterop;
  }
}
