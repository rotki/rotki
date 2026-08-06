import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import '@test/i18n';

const mocks = vi.hoisted(() => ({
  editAgnosticBlockchainAccount: vi.fn(),
  editBlockchainAccount: vi.fn(),
  editBtcAccount: vi.fn(),
  getNativeAsset: vi.fn((chain: string): string => chain.toUpperCase()),
  resetAddressNamesData: vi.fn(),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    editAgnosticBlockchainAccount: mocks.editAgnosticBlockchainAccount,
    editBlockchainAccount: mocks.editBlockchainAccount,
    editBtcAccount: mocks.editBtcAccount,
  })),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn(() => ({ resetAddressNamesData: mocks.resetAddressNamesData })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainName: (chain: string): string => chain,
    getNativeAsset: mocks.getNativeAsset,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function importModule(): Promise<typeof import('./use-account-edits')> {
  return import('./use-account-edits');
}

describe('useAccountEdits', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('editAccount', () => {
    it('should edit a btc account and reset address names for a non-xpub payload', async () => {
      mocks.editBtcAccount.mockResolvedValue({ standalone: [], xpubs: [] });
      const { useAccountEdits } = await importModule();
      const result = await useAccountEdits().editAccount({ address: 'bc1', tags: null }, 'btc');
      expect(mocks.editBtcAccount).toHaveBeenCalled();
      expect(result).toStrictEqual([]);
      expect(mocks.resetAddressNamesData).toHaveBeenCalledOnce();
    });

    it('should not reset address names for an xpub payload', async () => {
      mocks.editBtcAccount.mockResolvedValue({ standalone: [], xpubs: [] });
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useAccountEdits } = await importModule();
      await useAccountEdits().editAccount(xpubPayload, 'btc');
      expect(mocks.resetAddressNamesData).not.toHaveBeenCalled();
    });

    it('should edit an evm account and map the result into accounts', async () => {
      mocks.editBlockchainAccount.mockResolvedValue([{ address: '0xabc', label: null, tags: null }]);
      const { useAccountEdits } = await importModule();
      const result = await useAccountEdits().editAccount({ address: '0xabc', tags: null }, 'eth');
      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({ chain: 'eth', data: { address: '0xabc', type: 'address' }, nativeAsset: 'ETH' });
      expect(mocks.resetAddressNamesData).toHaveBeenCalledOnce();
    });
  });

  describe('editAgnosticAccount', () => {
    it('should edit the account and reset address names', async () => {
      mocks.editAgnosticBlockchainAccount.mockResolvedValue(true);
      const { useAccountEdits } = await importModule();
      const result = await useAccountEdits().editAgnosticAccount('evm', { address: '0xabc', tags: null });
      expect(result).toBe(true);
      expect(mocks.resetAddressNamesData).toHaveBeenCalledOnce();
    });
  });
});
