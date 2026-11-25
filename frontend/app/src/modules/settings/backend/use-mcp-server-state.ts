import type { StarlingServiceStatus } from '@shared/ipc';
import { set } from '@vueuse/shared';
import { readonly, type Ref, shallowRef } from 'vue';

const mcpServerState = shallowRef<StarlingServiceStatus>();

export function setMcpServerState(state: StarlingServiceStatus | undefined): void {
  set(mcpServerState, state);
}

export function useMcpServerState(): Readonly<Ref<StarlingServiceStatus | undefined>> {
  return readonly(mcpServerState);
}
