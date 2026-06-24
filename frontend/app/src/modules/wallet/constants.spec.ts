import { BaseError, UserRejectedRequestError } from 'viem';
import { describe, expect, it } from 'vitest';
import { getWalletErrorMessage, isUserRejectedError } from '@/modules/wallet/constants';

describe('isUserRejectedError', () => {
  it('should detect viem UserRejectedRequestError', () => {
    const error = new UserRejectedRequestError(new Error('User rejected the request.'));
    expect(isUserRejectedError(error)).toBe(true);
  });

  it('should detect a raw EIP-1193 4001 code', () => {
    expect(isUserRejectedError({ code: 4001, message: 'User denied' })).toBe(true);
  });

  it('should detect a 4001 code nested in a viem error cause chain', () => {
    // Mirrors the real bug: MetaMask rejection surfaces as a generic
    // "unknown RPC error" whose original 4001 only survives in the cause chain.
    const cause = Object.assign(
      new Error('MetaMask Tx Signature: User denied transaction signature.'),
      { code: 4001 },
    );
    const error = new BaseError('An unknown RPC error occurred.', { cause });
    expect(isUserRejectedError(error)).toBe(true);
  });

  it('should detect rejection via case-insensitive keyword match', () => {
    expect(isUserRejectedError(new Error('MetaMask Tx Signature: User denied transaction signature.'))).toBe(true);
    expect(isUserRejectedError(new Error('ACTION_REJECTED'))).toBe(true);
    expect(isUserRejectedError('User cancelled')).toBe(true);
  });

  it('should not flag unrelated errors as rejections', () => {
    expect(isUserRejectedError(new Error('insufficient funds for gas'))).toBe(false);
    expect(isUserRejectedError({ code: -32603, message: 'internal error' })).toBe(false);
    expect(isUserRejectedError(undefined)).toBe(false);
  });
});

describe('getWalletErrorMessage', () => {
  it('should prefer a viem error details line over the verbose message', () => {
    const error = new BaseError('An unknown RPC error occurred.', {
      details: 'MetaMask Tx Signature: User denied transaction signature.',
    });
    expect(getWalletErrorMessage(error)).toBe('MetaMask Tx Signature: User denied transaction signature.');
    // The verbose developer dump (request args, Version footer) is not shown.
    expect(getWalletErrorMessage(error)).not.toContain('Version:');
  });

  it('should fall back to the viem short message when no details exist', () => {
    const error = new BaseError('An unknown RPC error occurred.');
    expect(getWalletErrorMessage(error)).toBe('An unknown RPC error occurred.');
  });

  it('should return the message for a plain Error', () => {
    expect(getWalletErrorMessage(new Error('boom'))).toBe('boom');
  });

  it('should handle string and object errors', () => {
    expect(getWalletErrorMessage('plain string')).toBe('plain string');
    expect(getWalletErrorMessage({ message: 'object message' })).toBe('object message');
  });

  it('should fall back for an unknown error shape', () => {
    expect(getWalletErrorMessage(undefined)).toBe('Unknown error occurred');
  });
});
