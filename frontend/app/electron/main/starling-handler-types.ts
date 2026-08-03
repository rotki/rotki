import type { BackendCode, StarlingServiceStatus } from '@shared/ipc';

export interface StarlingErrorListener {
  onMcpState?: (state: StarlingServiceStatus) => void;
  onProcessError: (message: string | Error, code: BackendCode) => void;
}
