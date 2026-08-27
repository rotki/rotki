import type {
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  TransactionParams,
} from '@/modules/wallet/types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  handleTransactionError,
  prepareTransactionPayload,
  validateTransactionRequirements,
} from './transaction-helpers';

const FROM = '0xaaa';
const TO = '0xbbb';
const TOKEN = 'eip155:1/erc20:0xtoken';

function params(overrides: Partial<TransactionParams> = {}): TransactionParams {
  return { amount: '1.5', chain: 'ethereum', native: true, to: TO, ...overrides };
}

const namesEveryChain = (chain: string): string => chain;

describe('modules/wallet/validateTransactionRequirements', () => {
  it('should return the chain id, evm chain and sender when all are known', () => {
    const result = validateTransactionRequirements({
      connectedAddress: FROM,
      connectedChainId: 1,
      getEvmChainName: namesEveryChain,
      params: params(),
    });

    expect(result).toEqual({ chainId: 1, evmChain: 'ethereum', fromAddress: FROM });
  });

  it('should refuse when the wallet reports no chain', () => {
    expect(() => validateTransactionRequirements({
      connectedAddress: FROM,
      connectedChainId: undefined,
      getEvmChainName: namesEveryChain,
      params: params(),
    })).toThrow('No chain ID available');
  });

  it('should refuse when the chain is not a known evm chain', () => {
    expect(() => validateTransactionRequirements({
      connectedAddress: FROM,
      connectedChainId: 1,
      getEvmChainName: () => undefined,
      params: params({ chain: 'nonsense' }),
    })).toThrow('No chain ID available');
  });

  it('should refuse a chain id of zero rather than treating it as valid', () => {
    expect(() => validateTransactionRequirements({
      connectedAddress: FROM,
      connectedChainId: 0,
      getEvmChainName: namesEveryChain,
      params: params(),
    })).toThrow('No chain ID available');
  });

  it('should refuse when no wallet address is connected, past the chain guard', () => {
    expect(() => validateTransactionRequirements({
      connectedAddress: undefined,
      connectedChainId: 1,
      getEvmChainName: namesEveryChain,
      params: params(),
    })).toThrow('AssertionError');
  });
});

describe('modules/wallet/prepareTransactionPayload', () => {
  const prepareERC20Transfer = vi.fn(async (): Promise<PrepareERC20TransferResponse> => ({
    chainId: 1,
    data: '0xerc20data',
    from: FROM,
    nonce: 7,
    to: TOKEN,
    value: BigInt(0),
  }));

  const prepareNativeTransfer = vi.fn(async (): Promise<PrepareNativeTransferResponse> => ({
    from: FROM,
    nonce: 7,
    to: TO,
    value: BigInt('1500000000000000000'),
  }));

  const deps = { prepareERC20Transfer, prepareNativeTransfer };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('a native transfer', () => {
    it('should send the amount, the recipient and the evm chain', async () => {
      await prepareTransactionPayload(params({ native: true }), FROM, 'ethereum', deps);

      expect(prepareNativeTransfer).toHaveBeenCalledWith({
        amount: '1.5',
        chain: 'ethereum',
        fromAddress: FROM,
        toAddress: TO,
      });
      expect(prepareERC20Transfer).not.toHaveBeenCalled();
    });

    it('should add empty call data, which a native transfer carries', async () => {
      const result = await prepareTransactionPayload(params({ native: true }), FROM, 'ethereum', deps);

      expect(result.data).toBe('0x');
    });
  });

  describe('a token transfer', () => {
    it('should send the token rather than the chain', async () => {
      await prepareTransactionPayload(
        params({ assetIdentifier: TOKEN, native: false }),
        FROM,
        'ethereum',
        deps,
      );

      expect(prepareERC20Transfer).toHaveBeenCalledWith({
        amount: '1.5',
        fromAddress: FROM,
        toAddress: TO,
        token: TOKEN,
      });
      expect(prepareNativeTransfer).not.toHaveBeenCalled();
    });

    it('should return the prepared call data untouched', async () => {
      const result = await prepareTransactionPayload(
        params({ assetIdentifier: TOKEN, native: false }),
        FROM,
        'ethereum',
        deps,
      );

      expect(result.data).toBe('0xerc20data');
    });

    it('should refuse a token transfer that names no token', async () => {
      await expect(prepareTransactionPayload(
        params({ assetIdentifier: undefined, native: false }),
        FROM,
        'ethereum',
        deps,
      )).rejects.toThrow('AssertionError');

      expect(prepareERC20Transfer).not.toHaveBeenCalled();
    });
  });
});

describe('modules/wallet/handleTransactionError', () => {
  const setPreparing = vi.fn();
  const setWaitingForWalletConfirmation = vi.fn();
  const updateTransactionStatus = vi.fn();

  const handlers = { setPreparing, setWaitingForWalletConfirmation, updateTransactionStatus };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('should clear both in-flight flags', () => {
    handleTransactionError(new Error('boom'), handlers);

    expect(setPreparing).toHaveBeenCalledWith(false);
    expect(setWaitingForWalletConfirmation).toHaveBeenCalledWith(false);
  });

  it('should mark the transaction failed when the error names one', () => {
    handleTransactionError({ transaction: { hash: '0xdead' } }, handlers);

    expect(updateTransactionStatus).toHaveBeenCalledWith('0xdead', 'failed');
  });

  it.each([
    ['a plain error', new Error('boom')],
    ['null', null],
    ['undefined', undefined],
    ['a string', 'boom'],
    ['no transaction', { message: 'boom' }],
    ['a transaction with no hash', { transaction: {} }],
    ['a hash that is not a string', { transaction: { hash: 12345 } }],
    ['an empty hash', { transaction: { hash: '' } }],
  ])('should mark nothing failed for %s, while still clearing the flags', (_name, error) => {
    handleTransactionError(error, handlers);

    expect(updateTransactionStatus).not.toHaveBeenCalled();
    expect(setPreparing).toHaveBeenCalledWith(false);
    expect(setWaitingForWalletConfirmation).toHaveBeenCalledWith(false);
  });
});
