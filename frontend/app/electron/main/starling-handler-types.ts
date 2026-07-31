import type { BackendCode, McpServiceState } from '@shared/ipc';

export interface StarlingErrorListener {
  onMcpState?: (state: McpServiceState) => void;
  onProcessError: (message: string | Error, code: BackendCode) => void;
}
