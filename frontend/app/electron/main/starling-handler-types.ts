import type { BackendCode, StarlingServiceStatus } from '@shared/ipc';
import type { UnusableBinary } from '@shared/starling/binary-types';

export interface StarlingErrorListener {
  onMcpState?: (state: StarlingServiceStatus) => void;
  /**
   * @remarks
   * `unusableBinary` accompanies {@link BackendCode.MISSING_BINARY} and names the executable that
   * is gone, so the renderer can say which one in the user's own language.
   */
  onProcessError: (message: string | Error, code: BackendCode, unusableBinary?: UnusableBinary) => void;
}
