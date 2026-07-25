import {
  WalletBridgeNotConnectedError,
  WalletBridgeTimeoutError,
} from '@electron/main/wallet-bridge-errors';
import { describe, expect, it } from 'vitest';

describe('walletBridgeErrors', () => {
  it('should default to the JSON-RPC internal error code', () => {
    expect(new WalletBridgeNotConnectedError().code).toBe(-32603);
    expect(new WalletBridgeTimeoutError().code).toBe(-32603);
  });

  it('should keep its own name rather than the base class name', () => {
    expect(new WalletBridgeNotConnectedError().name).toBe('WalletBridgeNotConnectedError');
    expect(new WalletBridgeTimeoutError().name).toBe('WalletBridgeTimeoutError');
  });

  it('should carry a message describing the failure', () => {
    expect(new WalletBridgeNotConnectedError().message).toBe('Wallet bridge not connected');
    expect(new WalletBridgeTimeoutError().message).toBe('Request timeout');
  });

  it('should remain instances of Error so callers can catch them normally', () => {
    expect(new WalletBridgeNotConnectedError()).toBeInstanceOf(Error);
    expect(new WalletBridgeTimeoutError()).toBeInstanceOf(Error);
  });
});
