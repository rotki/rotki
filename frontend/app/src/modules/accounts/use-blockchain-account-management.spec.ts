import type { ComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { flushPromises } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { ActivityKind, ActivityPart, makeActivityId, type WorkStatus } from '@/modules/task-center/core/types';
import '@test/i18n';

const h = vi.hoisted(() => ({
  addAccounts: vi.fn(),
  completeAccountAddition: vi.fn(),
  fetchAccounts: vi.fn(),
  getNewAccountPayload: vi.fn(),
  notifyInfo: vi.fn(),
  refreshAccounts: vi.fn(),
}));

const mockAddRunning = ref<boolean>(false);

const NOTHING = { added: [], cancelled: false, failed: [], skipped: 0 };

const NO_OPTIONS = { parent: undefined, userStarted: undefined };

vi.mock('@/modules/accounts/use-account-addition-service', () => ({
  useAccountAdditionService: vi.fn(() => ({
    addAccounts: h.addAccounts,
    completeAccountAddition: h.completeAccountAddition,
    getNewAccountPayload: h.getNewAccountPayload,
  })),
}));

vi.mock('@/modules/accounts/use-account-operations', () => ({
  useAccountOperations: vi.fn(() => ({
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
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockAddRunning, false);
    h.completeAccountAddition.mockResolvedValue(undefined);
    h.addAccounts.mockResolvedValue(NOTHING);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addAccounts', () => {
    const payload = { modules: undefined, payload: [{ address: '0xabc', tags: null }] };

    it('should skip when an add-account task is already running', async () => {
      set(mockAddRunning, true);
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('eth', payload);
      expect(h.addAccounts).not.toHaveBeenCalled();
    });

    it('should not skip a row of a batch that is already running', async () => {
      set(mockAddRunning, true);
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      const { useBlockchainAccountManagement } = await importModule();

      await useBlockchainAccountManagement().addAccounts('eth', payload, {
        parent: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.ADD, 'batch'),
        wait: true,
      });

      expect(h.addAccounts).toHaveBeenCalledOnce();
    });

    it('should notify when there are no new addresses to add', async () => {
      h.getNewAccountPayload.mockReturnValue([]);
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('eth', payload);
      expect(h.notifyInfo).toHaveBeenCalledOnce();
      expect(h.addAccounts).not.toHaveBeenCalled();
    });

    it('should delegate the filtered payload through the same call for one address and for many', async () => {
      h.addAccounts.mockResolvedValue(NOTHING);
      const many = [{ address: '0xabc', tags: null }, { address: '0xdef', tags: null }];
      h.getNewAccountPayload.mockReturnValue(many);
      const { useBlockchainAccountManagement } = await importModule();

      await useBlockchainAccountManagement().addAccounts('eth', { modules: undefined, payload: many }, { wait: true });

      expect(h.addAccounts).toHaveBeenCalledWith('eth', many, undefined, expect.any(Function), NO_OPTIONS);
    });

    it('should pass userStarted through, so the dock opens only for an addition the caller says the user asked for', async () => {
      h.addAccounts.mockResolvedValue(NOTHING);
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      const { useBlockchainAccountManagement } = await importModule();

      await useBlockchainAccountManagement().addAccounts('eth', payload, { userStarted: true, wait: true });

      expect(h.addAccounts).toHaveBeenCalledWith('eth', expect.any(Array), undefined, expect.any(Function), { parent: undefined, userStarted: true });
    });

    it('should pass an xpub through unfiltered', async () => {
      h.addAccounts.mockResolvedValue(NOTHING);
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('btc', xpubPayload, { wait: true });

      expect(h.addAccounts).toHaveBeenCalledWith('btc', xpubPayload, [], expect.any(Function), NO_OPTIONS);
      expect(h.getNewAccountPayload).not.toHaveBeenCalled();
    });

    it('should return an empty summary when not awaiting because the addition is left detached', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      h.addAccounts.mockResolvedValue({ added: [{ address: '0xabc', chain: 'eth' }], cancelled: false, failed: [] });
      const { useBlockchainAccountManagement } = await importModule();

      expect(await useBlockchainAccountManagement().addAccounts('eth', payload)).toStrictEqual(NOTHING);
      await flushPromises();
      expect(h.addAccounts).toHaveBeenCalledOnce();
    });

    it('should return the summary when awaiting', async () => {
      const summary = { added: [{ address: '0xabc', chain: 'eth' }], cancelled: false, failed: [] };
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      h.addAccounts.mockResolvedValue(summary);
      const { useBlockchainAccountManagement } = await importModule();

      expect(await useBlockchainAccountManagement().addAccounts('eth', payload, { wait: true })).toStrictEqual(summary);
    });
  });

  describe('telling account detection what the user added', () => {
    const payload = { modules: undefined, payload: [{ address: '0xabc', tags: null }] };

    it('should record the addition before its result arrives, since the backend saves it first', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xABC', tags: null }]);
      h.addAccounts.mockReturnValue(new Promise(() => {}));
      const { useBlockchainAccountManagement } = await importModule();

      startPromise(useBlockchainAccountManagement().addAccounts('eth', payload, { wait: true }));

      expect(useDetectedAccountsStore().userAdditions).toEqual([{ addresses: ['0xabc'], chain: 'eth', finished: false, id: expect.any(Number) }]);
    });

    it('should keep the addition in flight until its accounts are read into the store, not just until the service resolves', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      let read: () => void = () => {};
      h.completeAccountAddition.mockReturnValue(new Promise<void>((resolve) => {
        read = resolve;
      }));
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('eth', payload, { wait: true });
      const onComplete = h.addAccounts.mock.calls[0]?.[3];
      assert(typeof onComplete === 'function');

      const completion = onComplete({ addedAccounts: [{ address: '0xabc', chain: 'eth' }], chain: 'eth' });
      const store = useDetectedAccountsStore();
      expect(store.userAdditions[0]?.finished).toBe(false);

      read();
      await completion;
      expect(store.userAdditions[0]?.finished).toBe(true);
    });

    it('should mark a failed addition finished too, so it does not hide detections forever', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      h.addAccounts.mockRejectedValue(new Error('boom'));
      const { useBlockchainAccountManagement } = await importModule();

      await expect(useBlockchainAccountManagement().addAccounts('eth', payload, { wait: true })).rejects.toThrow('boom');

      expect(useDetectedAccountsStore().userAdditions[0]?.finished).toBe(true);
    });

    it('should record an addition to every EVM chain as covering any chain', async () => {
      h.getNewAccountPayload.mockReturnValue([{ address: '0xabc', tags: null }]);
      const { useBlockchainAccountManagement } = await importModule();

      await useBlockchainAccountManagement().addAccounts(EVM_PSEUDO_CHAIN, payload, { wait: true });

      expect(useDetectedAccountsStore().wasAddedByUser({ address: '0xABC', chain: 'optimism' })).toBe(true);
    });

    it('should record nothing for an xpub, which detection never touches', async () => {
      const { useBlockchainAccountManagement } = await importModule();

      await useBlockchainAccountManagement().addAccounts('btc', { tags: null, xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB } }, { wait: true });

      expect(useDetectedAccountsStore().userAdditions).toEqual([]);
    });
  });

  describe('passthrough exports', () => {
    it('should re-expose the account operation helpers', async () => {
      const { useBlockchainAccountManagement } = await importModule();
      const management = useBlockchainAccountManagement();
      expect(management.fetchAccounts).toBe(h.fetchAccounts);
      expect(management.refreshAccounts).toBe(h.refreshAccounts);
    });
  });
});
