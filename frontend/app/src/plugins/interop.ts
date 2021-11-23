/* istanbul ignore file */

import _Vue from 'vue';
import { ElectronInterop, interop } from '@/electron-interop';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Interop(vue: typeof _Vue, options?: any): void {
  vue.prototype.$interop = interop;
}

declare module 'vue/types/vue' {
  interface Vue {
    $interop: ElectronInterop;
  }
}
