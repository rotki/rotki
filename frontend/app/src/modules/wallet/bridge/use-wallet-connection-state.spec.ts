import { beforeEach, describe, expect, it } from 'vitest';
import { useWalletConnectionState } from '@/modules/wallet/bridge/use-wallet-connection-state';

describe('useWalletConnectionState', () => {
  beforeEach(() => {
    const { setRequestingAccounts } = useWalletConnectionState();
    setRequestingAccounts(false);
  });

  it('should default isRequestingAccounts to false', () => {
    const { isRequestingAccounts } = useWalletConnectionState();
    expect(get(isRequestingAccounts)).toBe(false);
  });

  it('should toggle isRequestingAccounts via setRequestingAccounts', () => {
    const { isRequestingAccounts, setRequestingAccounts } = useWalletConnectionState();

    setRequestingAccounts(true);
    expect(get(isRequestingAccounts)).toBe(true);

    setRequestingAccounts(false);
    expect(get(isRequestingAccounts)).toBe(false);
  });

  it('should set requesting=true during a tracked promise and reset to false on resolve', async () => {
    const { isRequestingAccounts, trackAccountsRequest } = useWalletConnectionState();

    let observedDuringPromise = false;
    const promise = new Promise<string>((resolve) => {
      setTimeout(() => {
        observedDuringPromise = get(isRequestingAccounts);
        resolve('done');
      }, 0);
    });

    const result = await trackAccountsRequest(promise);

    expect(result).toBe('done');
    expect(observedDuringPromise).toBe(true);
    expect(get(isRequestingAccounts)).toBe(false);
  });

  it('should reset isRequestingAccounts to false even when the promise rejects', async () => {
    const { isRequestingAccounts, trackAccountsRequest } = useWalletConnectionState();

    await expect(trackAccountsRequest(Promise.reject(new Error('boom')))).rejects.toThrow('boom');
    expect(get(isRequestingAccounts)).toBe(false);
  });

  it('should share state across composable calls', () => {
    const first = useWalletConnectionState();
    first.setRequestingAccounts(true);

    const second = useWalletConnectionState();
    expect(get(second.isRequestingAccounts)).toBe(true);
  });
});
