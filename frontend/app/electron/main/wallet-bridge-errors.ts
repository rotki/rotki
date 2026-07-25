/**
 * Custom error classes for wallet bridge operations
 */

/** JSON-RPC internal error, the code every bridge failure reports today. */
const INTERNAL_ERROR_CODE = -32603;

class WalletBridgeError extends Error {
  readonly code: number;

  constructor(message: string, options: ErrorOptions & { code?: number } = {}) {
    super(message, options);
    this.code = options.code ?? INTERNAL_ERROR_CODE;
    this.name = 'WalletBridgeError';
  }
}

export class WalletBridgeNotConnectedError extends WalletBridgeError {
  constructor() {
    super('Wallet bridge not connected');
    this.name = 'WalletBridgeNotConnectedError';
  }
}

export class WalletBridgeTimeoutError extends WalletBridgeError {
  constructor() {
    super('Request timeout');
    this.name = 'WalletBridgeTimeoutError';
  }
}
