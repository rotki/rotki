import { Blockchain } from '@rotki/common';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { Module } from '@/modules/core/common/modules';
import '@test/i18n';

const h = vi.hoisted(() => ({
  addAccount: vi.fn(),
  addEvmAccount: vi.fn(),
  createFailureNotification: vi.fn(),
  detectTokens: vi.fn(),
  enableModule: vi.fn(),
  fetchTags: vi.fn(),
  getAddresses: vi.fn((): string[] => []),
  notifyFailedToAddAddress: vi.fn(),
  notifyUser: vi.fn(),
  supportsTransactions: vi.fn((): boolean => true),
  trackAddedAddresses: vi.fn(),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts', () => ({
  useBlockchainAccounts: vi.fn(() => ({ addAccount: h.addAccount, addEvmAccount: h.addEvmAccount })),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(() => ({ detectTokens: h.detectTokens })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({ trackAddedAddresses: h.trackAddedAddresses })),
}));

vi.mock('@/modules/tags/use-tag-operations', () => ({
  useTagOperations: vi.fn(() => ({ fetchTags: h.fetchTags })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({ enableModule: h.enableModule })),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn(() => ({ getAddresses: h.getAddresses })),
}));

vi.mock('@/modules/accounts/use-account-addition-notifications', () => ({
  useAccountAdditionNotifications: vi.fn(() => ({
    createFailureNotification: h.createFailureNotification,
    notifyFailedToAddAddress: h.notifyFailedToAddAddress,
    notifyUser: h.notifyUser,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { ref } = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      evmChains: ref(['eth', 'optimism']),
      supportsTransactions: h.supportsTransactions,
    })),
  };
});

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function importModule(): Promise<typeof import('./use-account-addition-service')> {
  return import('./use-account-addition-service');
}

describe('useAccountAdditionService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.getAddresses.mockReturnValue([]);
    h.supportsTransactions.mockReturnValue(true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getNewAccountPayload', () => {
    it('should filter out already known addresses case-insensitively', async () => {
      h.getAddresses.mockReturnValue(['0xabc']);
      const { useAccountAdditionService } = await importModule();
      const result = useAccountAdditionService().getNewAccountPayload('eth', [
        { address: '0xABC', tags: null },
        { address: '0xdef', tags: null },
      ]);
      expect(result).toEqual([{ address: '0xdef', tags: null }]);
    });
  });

  describe('addSingleAccount', () => {
    it('should return the address on success', async () => {
      h.addAccount.mockResolvedValue('0xabc');
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleAccount({ address: '0xabc', tags: null }, 'eth');
      expect(h.addAccount).toHaveBeenCalledWith('eth', [{ address: '0xabc', tags: null }]);
      expect(result).toStrictEqual({ address: '0xabc', type: 'success' });
    });

    it('should pass an xpub payload through directly', async () => {
      h.addAccount.mockResolvedValue('xpub123');
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleAccount(xpubPayload, 'btc');
      expect(h.addAccount).toHaveBeenCalledWith('btc', xpubPayload);
      expect(result).toStrictEqual({ address: 'xpub123', type: 'success' });
    });

    it('should return an error result when the addition throws', async () => {
      h.addAccount.mockRejectedValue(new Error('nope'));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleAccount({ address: '0xabc', tags: null }, 'eth');
      expect(result.type).toBe('error');
    });
  });

  describe('addSingleEvmAddress', () => {
    it('should expand added chains and notify the user', async () => {
      h.addEvmAccount.mockResolvedValue({ added: { '0xabc': ['eth', 'optimism'] } });
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(result.type === 'success');
      expect(result.accounts).toEqual([
        { address: '0xabc', chain: 'eth' },
        { address: '0xabc', chain: 'optimism' },
      ]);
      expect(h.notifyUser).toHaveBeenCalledOnce();
      expect(h.createFailureNotification).toHaveBeenCalledOnce();
    });

    it('should expand to all evm chains when the result is "all"', async () => {
      h.addEvmAccount.mockResolvedValue({ added: { '0xabc': ['all'] } });
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(result.type === 'success');
      expect(result.accounts.map(a => a.chain)).toEqual(['eth', 'optimism']);
    });

    it('should skip chains that are not valid blockchains', async () => {
      h.addEvmAccount.mockResolvedValue({ added: { '0xabc': ['eth', 'not-a-chain'] } });
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(result.type === 'success');
      expect(result.accounts.map(a => a.chain)).toEqual(['eth']);
    });

    it('should return an error result when the addition throws', async () => {
      h.addEvmAccount.mockRejectedValue(new Error('boom'));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      expect(result.type).toBe('error');
    });
  });

  describe('addMultipleAccounts', () => {
    it('should collect added accounts and invoke the completion callback', async () => {
      h.addAccount.mockResolvedValue('0xabc');
      const onComplete = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().addMultipleAccounts(
        [{ address: '0xabc', tags: null }],
        'eth',
        undefined,
        onComplete,
      );
      expect(onComplete).toHaveBeenCalledWith({ addedAccounts: [{ address: '0xabc', chain: 'eth' }], chain: 'eth', modulesToEnable: undefined });
      expect(h.notifyFailedToAddAddress).not.toHaveBeenCalled();
    });

    it('should notify about failed additions', async () => {
      h.addAccount.mockRejectedValue(new Error('nope'));
      const onComplete = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().addMultipleAccounts(
        [{ address: '0xabc', tags: null }],
        'eth',
        undefined,
        onComplete,
      );
      expect(h.notifyFailedToAddAddress).toHaveBeenCalledOnce();
    });
  });

  describe('addMultipleEvmAccounts', () => {
    it('should collect added accounts and invoke the completion callback', async () => {
      h.addEvmAccount.mockResolvedValue({ added: { '0xabc': ['eth'] } });
      const onComplete = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().addMultipleEvmAccounts(
        { modules: undefined, payload: [{ address: '0xabc', tags: null }] },
        onComplete,
      );
      expect(onComplete).toHaveBeenCalledWith({ addedAccounts: [{ address: '0xabc', chain: 'eth' }], modulesToEnable: undefined });
      expect(h.notifyFailedToAddAddress).not.toHaveBeenCalled();
    });

    it('should notify about failed evm additions', async () => {
      h.addEvmAccount.mockRejectedValue(new Error('boom'));
      const onComplete = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().addMultipleEvmAccounts(
        { modules: undefined, payload: [{ address: '0xabc', tags: null }] },
        onComplete,
      );
      expect(h.notifyFailedToAddAddress).toHaveBeenCalledOnce();
    });
  });

  describe('completeAccountAddition', () => {
    const added = [{ address: '0xabc', chain: Blockchain.ETH }];

    it('should fetch account metadata for transaction-supporting chains', async () => {
      const onRefreshAccounts = vi.fn<() => Promise<void>>(async () => {});
      const onFetchAccounts = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().completeAccountAddition(
        { addedAccounts: added, chain: 'eth' },
        onRefreshAccounts,
        onFetchAccounts,
      );
      expect(h.fetchTags).toHaveBeenCalledOnce();
      expect(h.trackAddedAddresses).toHaveBeenCalledWith(['0xabc']);
      expect(onFetchAccounts).toHaveBeenCalledWith('eth', true);
      expect(onRefreshAccounts).not.toHaveBeenCalled();
      expect(h.detectTokens).toHaveBeenCalledWith('eth', ['0xabc']);
    });

    it('should refresh accounts when the chain does not support transactions', async () => {
      h.supportsTransactions.mockReturnValue(false);
      const onRefreshAccounts = vi.fn<() => Promise<void>>(async () => {});
      const onFetchAccounts = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().completeAccountAddition(
        { addedAccounts: added, chain: 'btc', isXpub: true },
        onRefreshAccounts,
        onFetchAccounts,
      );
      expect(onRefreshAccounts).toHaveBeenCalledWith({ addresses: ['0xabc'], blockchain: 'btc', isXpub: true });
      expect(onFetchAccounts).not.toHaveBeenCalled();
      expect(h.detectTokens).not.toHaveBeenCalled();
    });

    it('should enable the requested modules for eth accounts', async () => {
      const onRefreshAccounts = vi.fn<() => Promise<void>>(async () => {});
      const onFetchAccounts = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().completeAccountAddition(
        { addedAccounts: added, chain: 'eth', modulesToEnable: [Module.ETH2] },
        onRefreshAccounts,
        onFetchAccounts,
      );
      expect(h.enableModule).toHaveBeenCalledWith({ addresses: ['0xabc'], enable: [Module.ETH2] });
    });
  });
});
