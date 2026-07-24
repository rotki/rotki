import type { BackendCode, McpServiceState } from '@shared/ipc';

export interface StarlingErrorListener {
  onMcpState?: (state: McpServiceState) => void;
  onProcessError: (message: string | Error, code: BackendCode) => void;
}

export interface JsonRpcResponse {
  jsonrpc: '2.0';
  id?: number;
  result?: unknown;
  error?: { code: number; message: string };
  method?: string;
  params?: unknown;
}
