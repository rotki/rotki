import type { ComputedRef } from 'vue';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { ActivityKind, ActivityPart, makeActivityId, type WorkStatus } from '@/modules/task-center/core/types';
import '@test/i18n';

const h = vi.hoisted(() => ({
  addAccounts: vi.fn(),
  completeAccountAddition: vi.fn(),
  detectEvmAccounts: vi.fn(),
  fetchAccounts: vi.fn(),
  getNewAccountPayload: vi.fn(),
  notifyInfo: vi.fn(),
  refreshAccounts: vi.fn(),
}));

const mockAddRunning = ref<boolean>(false);

const NOTHING = { added: [], cancelled: false, failed: [] };

vi.mock('@/modules/accounts/use-account-addition-service', () => ({
  useAccountAdditionService: vi.fn(() => ({
    addAccounts: h.addAccounts,
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

    // The guard stops a user submitting the form twice, not a batch from proceeding. A CSV import
    // fans its rows out at once, so from row two onwards an addition is always already running —
    // without this the import silently dropped every row but the first while its progress bar and
    // completion message both still counted them.
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

    // The address count no longer selects a mechanism: one and many take the same call, and the
    // batch decides whether an umbrella is warranted.
    it('should delegate the filtered payload for one address and for many', async () => {
      h.addAccounts.mockResolvedValue(NOTHING);
      const many = [{ address: '0xabc', tags: null }, { address: '0xdef', tags: null }];
      h.getNewAccountPayload.mockReturnValue(many);
      const { useBlockchainAccountManagement } = await importModule();

      await useBlockchainAccountManagement().addAccounts('eth', { modules: undefined, payload: many }, { wait: true });

      expect(h.addAccounts).toHaveBeenCalledWith('eth', many, undefined, expect.any(Function), undefined);
    });

    it('should pass an xpub through unfiltered', async () => {
      h.addAccounts.mockResolvedValue(NOTHING);
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useBlockchainAccountManagement } = await importModule();
      await useBlockchainAccountManagement().addAccounts('btc', xpubPayload, { wait: true });

      expect(h.addAccounts).toHaveBeenCalledWith('btc', xpubPayload, [], expect.any(Function), undefined);
      expect(h.getNewAccountPayload).not.toHaveBeenCalled();
    });

    // Without `wait` the addition is detached, so there is nothing to report back yet.
    it('should return an empty summary when not awaiting', async () => {
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
