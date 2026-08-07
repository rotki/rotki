import { FetchError } from 'ofetch';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

function unauthorized(): FetchError {
  const error = new FetchError('No user is currently logged in');
  error.status = 401;
  return error;
}

const mocks = vi.hoisted(() => ({
  fetchEthStakingValidators: vi.fn(),
  getNativeAsset: vi.fn((chain: string): string => chain.toUpperCase()),
  notifyError: vi.fn(),
  queryAccounts: vi.fn(),
  queryBtcAccounts: vi.fn(),
  updateAccounts: vi.fn(),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    queryAccounts: mocks.queryAccounts,
    queryBtcAccounts: mocks.queryBtcAccounts,
  })),
}));

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: vi.fn(() => ({ fetchEthStakingValidators: mocks.fetchEthStakingValidators })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({ updateAccounts: mocks.updateAccounts })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainName: (chain: string): string => chain,
    getNativeAsset: mocks.getNativeAsset,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
  useNotifications: vi.fn(() => ({ notifyError: mocks.notifyError })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function importModule(): Promise<typeof import('./use-account-fetching')> {
  return import('./use-account-fetching');
}

describe('useAccountFetching', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch btc accounts for a btc chain', async () => {
    mocks.queryBtcAccounts.mockResolvedValue({ standalone: [], xpubs: [] });
    const { useAccountFetching } = await importModule();
    await useAccountFetching().fetch('btc');
    expect(mocks.queryBtcAccounts).toHaveBeenCalledWith('btc');
    expect(mocks.updateAccounts).toHaveBeenCalledWith('btc', []);
  });

  it('should fetch eth staking validators for eth2', async () => {
    const { useAccountFetching } = await importModule();
    await useAccountFetching().fetch('eth2');
    expect(mocks.fetchEthStakingValidators).toHaveBeenCalledOnce();
  });

  it('should fetch blockchain accounts for a regular chain', async () => {
    mocks.queryAccounts.mockResolvedValue([{ address: '0xabc', label: null, tags: null }]);
    const { useAccountFetching } = await importModule();
    await useAccountFetching().fetch('eth');
    expect(mocks.queryAccounts).toHaveBeenCalledWith('eth');
    expect(mocks.updateAccounts).toHaveBeenCalledOnce();
  });

  it('should notify when fetching blockchain accounts fails', async () => {
    mocks.queryAccounts.mockRejectedValue(new Error('query failed'));
    const { useAccountFetching } = await importModule();
    await useAccountFetching().fetch('eth');
    expect(mocks.notifyError).toHaveBeenCalledOnce();
  });

  it('should notify when fetching btc accounts fails', async () => {
    mocks.queryBtcAccounts.mockRejectedValue(new Error('btc failed'));
    const { useAccountFetching } = await importModule();
    await useAccountFetching().fetch('bch');
    expect(mocks.notifyError).toHaveBeenCalledOnce();
  });

  // This runs once per supported chain, so a logout mid-flight raised one notification per chain.
  // They stack at `z-[10000]` over the user menu and swallow clicks — the notification is about a
  // session `handleAuthFailure` has already torn down.
  it('should stay silent when the session expired', async () => {
    mocks.queryAccounts.mockRejectedValue(unauthorized());
    const { useAccountFetching } = await importModule();

    await useAccountFetching().fetch('eth');

    expect(mocks.notifyError).not.toHaveBeenCalled();
  });

  // The guard must key on the status, not on "it came from the accounts query" — otherwise it
  // swallows every real backend failure on this path too.
  it('should still notify for a non-401 FetchError', async () => {
    const error = new FetchError('boom');
    error.status = 500;
    mocks.queryAccounts.mockRejectedValue(error);
    const { useAccountFetching } = await importModule();

    await useAccountFetching().fetch('eth');

    expect(mocks.notifyError).toHaveBeenCalledOnce();
  });
});
