import type { McpServiceState } from '@shared/ipc';
import type { Ref } from 'vue';

const mcpServerState = shallowRef<McpServiceState>();

export function setMcpServerState(state: McpServiceState | undefined): void {
  set(mcpServerState, state);
}

export function useMcpServerState(): Readonly<Ref<McpServiceState | undefined>> {
  return readonly(mcpServerState);
}
