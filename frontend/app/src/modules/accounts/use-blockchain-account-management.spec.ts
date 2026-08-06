import type { ComputedRef } from 'vue';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AddAccountsPayload, type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import '@test/i18n';

const h = vi.hoisted(() => ({
  addMultipleAccounts: vi.fn(),
  addMultipleEvmAccounts: vi.fn(),
  addSingleAccount: vi.fn(),
  addSingleEvmAddress: vi.fn(),
  completeAccountAddition: vi.fn(),
  detectEvmAccounts: vi.fn(),
  fetchAccounts: vi.fn(),
  getNewAccountPayload: vi.fn(),
  notifyInfo: vi.fn(),
  refreshAccounts: vi.fn(),
}));

const mockAddRunning = ref<boolean>(false);

vi.mock('@/modules/accounts/use-account-addition-service', () => ({
  useAccountAdditionService: vi.fn(() => ({
    addMultipleAccounts: h.addMultipleAccounts,
    addMultipleEvmAccounts: h.addMultipleEvmAccounts,
    addSingleAccount: h.addSingleAccount,
    addSingleEvmAddress: h.addSingleEvmAddress,
    completeAccountAddition: h.completeAccountAddition,
    getNewAccountPayload: h.getNewAccountPayload,
  })),
}));

vi.mock('@/modules/accounts/use-account-operations', () => ({
  useAccountOperations: vi.fn(() => ({
    detectEvmAccounts: h.detectEvmAccounts,
    fetchAccounts: h.fetchAccounts,
    refreshAccounts: h.refreshAccounts,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getChainName: (chain: string): string => chain })),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useWorkStatusPrefix: (_kind: string, part?: string): ComputedRef<WorkStatus> => computed<WorkStatus>(() => {
      const active = part === 'add' ? get(mockAddRunning) : false;
      return { active, everCompleted: false, pending: false, running: active };
    }),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyInfo: h.notifyInfo })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function importModule(): Promise<typeof import('./use-blockchain-account-management')> {
  return import('./use-blockchain-account-management');
}

describe('useBlockchainAccountManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockAddRunning, false);
    h.completeAccountAddition.mockResolvedValue(undefined);
    h.addMultipleEvmAccounts.mockResolvedValue(undefined);
    h.addMultipleAccounts.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addEvmAccounts', () => {
    it('should add a single evm address and complete the addition', async () => {
      h.addSingleEvmAddress.mockResolvedValue({ accounts: [{ address: '0xabc', chain: 'eth' }], type: 'success' });
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addEvmAccounts({ modules: undefined, payload: [{ address: '0xabc', tags: null }] });
      expect(h.addSingleEvmAddress).toHaveBeenCalledWith({ address: '0xabc', tags: null });
      await flushPromises();
      expect(h.completeAccountAddition).toHaveBeenCalledWith(
        { addedAccounts: [{ address: '0xabc', chain: 'eth' }], modulesToEnable: undefined },
        h.refreshAccounts,
        h.fetchAccounts,
      );
    });

    it('should throw when a single evm addition fails', async () => {
      h.addSingleEvmAddress.mockResolvedValue({ account: { address: '0xabc', tags: null }, error: new Error('boom'), type: 'error' });
      const { useBlockchainAccountManagement } = await importModule();
      await expect(
        useBlockchainAccountManagement().addEvmAccounts({ modules: undefined, payload: [{ address: '0xabc', tags: null }] }),
      ).rejects.toThrow('boom');
    });

    it('should await multiple evm additions when wait is set', async () => {
      const payload: AddAccountsPayload = { modules: undefined, payload: [
        { address: '0xabc', tags: null },
        { address: '0xdef', tags: null },
      ] };
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addEvmAccounts(payload, { wait: true });
      expect(h.addMultipleEvmAccounts).toHaveBeenCalledOnce();
    });
  });

  describe('addAccounts', () => {
    it('should skip when an add-account task is already running', async () => {
      set(mockAddRunning, true);
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('eth', { modules: undefined, payload: [{ address: '0xabc', tags: null }] });
      expect(h.addSingleAccount).not.toHaveBeenCalled();
    });

    it('should notify when there are no new addresses to add', async () => {
      h.getNewAccountPayload.mockReturnValue([]);
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('eth', { modules: undefined, payload: [{ address: '0xabc', tags: null }] });
      expect(h.notifyInfo).toHaveBeenCalledOnce();
      expect(h.addSingleAccount).not.toHaveBeenCalled();
    });

    it('should add a single new account and complete the addition', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      h.addSingleAccount.mockResolvedValue({ address: '0xabc', type: 'success' });
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('eth', { modules: undefined, payload: [{ address: '0xabc', tags: null }] });
      expect(h.addSingleAccount).toHaveBeenCalledWith({ address: '0xabc', tags: null }, 'eth');
      await flushPromises();
      expect(h.completeAccountAddition).toHaveBeenCalledOnce();
    });

    it('should add an xpub account directly', async () => {
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      h.addSingleAccount.mockResolvedValue({ address: 'xpub123', type: 'success' });
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('btc', xpubPayload);
      expect(h.addSingleAccount).toHaveBeenCalledWith(xpubPayload, 'btc');
      expect(h.getNewAccountPayload).not.toHaveBeenCalled();
    });

    it('should throw when a single account addition fails', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      h.addSingleAccount.mockResolvedValue({ account: { address: '0xabc', tags: null }, error: new Error('nope'), type: 'error' });
      const { useBlockchainAccountManagement } = await importModule();
      await expect(
        useBlockchainAccountManagement().addAccounts('eth', { modules: undefined, payload: [{ address: '0xabc', tags: null }] }),
      ).rejects.toThrow('nope');
    });
  });

  describe('passthrough exports', () => {
    it('should re-expose the account operation helpers', async () => {
      const { useBlockchainAccountManagement } = await importModule();
      const management = useBlockchainAccountManagement();
      expect(management.detectEvmAccounts).toBe(h.detectEvmAccounts);
      expect(management.fetchAccounts).toBe(h.fetchAccounts);
      expect(management.refreshAccounts).toBe(h.refreshAccounts);
    });
  });
});
