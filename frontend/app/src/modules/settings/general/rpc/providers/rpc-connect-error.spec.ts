import { describe, expect, it } from 'vitest';
import {
  RPC_CONNECT_ERROR,
  summariseRpcConnectError,
  tidyRpcConnectMessage,
} from '@/modules/settings/general/rpc/providers/rpc-connect-error';

describe('settings/general/rpc/providers/rpc-connect-error', () => {
  it('should read a plain connection failure as unreachable', () => {
    const message = 'Failed to connect to ethereum node NodeName(name=\'Infura\') at endpoint https://mainnet.infura.io/v3/key';

    expect(summariseRpcConnectError(message)).toBe(RPC_CONNECT_ERROR.UNREACHABLE);
  });

  it('should prefer the rejected key when the message is both', () => {
    const message = 'Failed to connect to Solana RPC at https://solana-mainnet.infura.io/v3/key due to 401 Client Error';

    expect(summariseRpcConnectError(message)).toBe(RPC_CONNECT_ERROR.REJECTED);
  });

  it.each([
    ['401', 'request failed with 401'],
    ['403', 'got a 403 back'],
    ['unauthorized', 'Unauthorized'],
    ['invalid key', 'invalid api key supplied'],
  ])('should read %s as a rejected key', (_case, message) => {
    expect(summariseRpcConnectError(message)).toBe(RPC_CONNECT_ERROR.REJECTED);
  });

  it('should read a chain mismatch as the wrong network', () => {
    const message = 'Connected to node at endpoint https://x but it is not on the right network';

    expect(summariseRpcConnectError(message)).toBe(RPC_CONNECT_ERROR.WRONG_NETWORK);
  });

  it('should not guess at a message it does not recognise', () => {
    expect(summariseRpcConnectError('something else entirely')).toBe(RPC_CONNECT_ERROR.UNKNOWN);
    expect(summariseRpcConnectError('')).toBe(RPC_CONNECT_ERROR.UNKNOWN);
  });

  describe('tidyRpcConnectMessage', () => {
    it('should drop the node repr, the chain and the second copy of the endpoint', () => {
      const message = 'Failed to connect to ethereum node NodeName(name=\'Infura\', endpoint=\'https://mainnet.infura.io/v3/dead…beef\', owned=True, blockchain=<SupportedBlockchain.ETHEREUM: \'ETH\'>) at endpoint https://mainnet.infura.io/v3/dead…beef';

      expect(tidyRpcConnectMessage(message)).toBe('Failed to connect at endpoint https://mainnet.infura.io/v3/dead…beef');
    });

    it('should keep the cause and drop only the repeated endpoint', () => {
      const message = 'Failed to connect to Solana RPC at https://solana-mainnet.infura.io/v3/dead…beef due to 401 Client Error: Unauthorized for url: https://solana-mainnet.infura.io/v3/dead…beef';

      expect(tidyRpcConnectMessage(message)).toBe('Failed to connect to Solana RPC at https://solana-mainnet.infura.io/v3/dead…beef due to 401 Client Error: Unauthorized');
    });

    it('should keep two endpoints that differ', () => {
      const message = 'Connected to https://one.example at endpoint https://two.example';

      expect(tidyRpcConnectMessage(message)).toBe(message);
    });

    it('should pass a message of another shape through untouched', () => {
      expect(tidyRpcConnectMessage('something else entirely')).toBe('something else entirely');
      expect(tidyRpcConnectMessage('')).toBe('');
    });
  });
});
