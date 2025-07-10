/**
 * Custom error classes for wallet bridge operations
 */

export class WalletBridgeError extends Error {
  constructor(message: string, public readonly code: number = -32603) {
    super(message);
    this.name = 'WalletBridgeError';
  }
}

export class WalletBridgeNotConnectedError extends WalletBridgeError {
  constructor() {
    super('Wallet bridge not connected', -32603);
    this.name = 'WalletBridgeNotConnectedError';
  }
}

export class WalletBridgeTimeoutError extends WalletBridgeError {
  constructor() {
    super('Request timeout', -32603);
    this.name = 'WalletBridgeTimeoutError';
  }
}
