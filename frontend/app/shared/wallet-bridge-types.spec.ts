import { assert, describe, expect, it } from 'vitest';
import { parseWalletBridgeMessage } from './wallet-bridge-types';

describe('shared/wallet-bridge-types', () => {
  describe('parseWalletBridgeMessage', () => {
    it('should parse a request', () => {
      const result = parseWalletBridgeMessage(JSON.stringify({ id: 1, jsonrpc: '2.0', method: 'eth_chainId' }));

      assert(result.ok);
      expect(result.value).toMatchObject({ id: 1, method: 'eth_chainId' });
    });

    it('should parse a notification', () => {
      const result = parseWalletBridgeMessage(JSON.stringify({ type: 'close_tab' }));

      assert(result.ok);
      expect(result.value).toMatchObject({ type: 'close_tab' });
    });

    it('should report text that is not JSON as invalid-json', () => {
      const result = parseWalletBridgeMessage('{"id":1,');

      assert(!result.ok);
      expect(result.error.kind).toBe('invalid-json');
    });

    it('should report JSON outside the schema as invalid-message and keep the decoded value', () => {
      const result = parseWalletBridgeMessage(JSON.stringify({ id: 7, jsonrpc: '1.0' }));

      assert(!result.ok);
      assert(result.error.kind === 'invalid-message');
      expect(result.error.raw).toEqual({ id: 7, jsonrpc: '1.0' });
    });

    it('should reject a response carrying both a result and an error', () => {
      const result = parseWalletBridgeMessage(JSON.stringify({
        error: { code: 1, message: 'x' },
        id: 1,
        jsonrpc: '2.0',
        result: '0x1',
      }));

      assert(!result.ok);
      expect(result.error.kind).toBe('invalid-message');
    });
  });
});
