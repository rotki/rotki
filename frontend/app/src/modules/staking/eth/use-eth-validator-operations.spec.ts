import type { ComputedRef } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { bigNumberify, Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEthValidatorOperations } from '@/modules/staking/eth/use-eth-validator-operations';

const mockShowConfirmation = vi.fn();
const mockFetchEthStakingValidators = vi.fn();
const mockRefreshBlockchainBalances = vi.fn();
const mockLoading = ref<boolean>(false);
const mockAddRunning = ref<boolean>(false);
const mockRemoveRunning = ref<boolean>(false);

vi.mock('@/modules/accounts/blockchain/use-account-delete', () => ({
  useAccountDelete: (): { showConfirmation: typeof mockShowConfirmation } => ({ showConfirmation: mockShowConfirmation }),
}));

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: (): { fetchEthStakingValidators: typeof mockFetchEthStakingValidators } => ({
    fetchEthStakingValidators: mockFetchEthStakingValidators,
  }),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: (): { refreshBlockchainBalances: typeof mockRefreshBlockchainBalances } => ({
    refreshBlockchainBalances: mockRefreshBlockchainBalances,
  }),
}));

function activeFor(part?: string): boolean {
  if (part === 'add')
    return get(mockAddRunning);
  if (part === 'remove')
    return get(mockRemoveRunning);
  if (part === 'eth2')
    return get(mockLoading);
  return false;
}

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useIsActivePrefix: (_kind: string, part?: string): ComputedRef<boolean> => computed<boolean>(() => activeFor(part)),
    useWorkStatusPrefix: (_kind: string, part?: string): ComputedRef<WorkStatus> => computed<WorkStatus>(() => {
      const active = activeFor(part);
      return { active, everCompleted: false, pending: false, running: active };
    }),
  }),
}));

function validator(overrides: Partial<EthereumValidator> = {}): EthereumValidator {
  return {
    amount: bigNumberify(32),
    index: 1,
    publicKey: '0xabc',
    status: 'active',
    type: 'validator',
    value: bigNumberify(64000),
    ...overrides,
  };
}

describe('useEthValidatorOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockLoading, false);
    set(mockAddRunning, false);
    set(mockRemoveRunning, false);
  });

  describe('edit', () => {
    it('should map a validator into an edit manage payload', () => {
      const { edit } = useEthValidatorOperations();
      expect(edit(validator({ index: 42, ownershipPercentage: '50', publicKey: '0xdef' }))).toEqual({
        chain: Blockchain.ETH2,
        data: { ownershipPercentage: '50', publicKey: '0xdef', validatorIndex: '42' },
        mode: 'edit',
        type: 'validator',
      });
    });

    it('should default the ownership percentage to 100', () => {
      const { edit } = useEthValidatorOperations();
      expect(edit(validator()).data.ownershipPercentage).toBe('100');
    });
  });

  describe('refresh', () => {
    it('should refetch validators ignoring cache then refresh balances', async () => {
      const { refresh } = useEthValidatorOperations();
      await refresh();
      expect(mockFetchEthStakingValidators).toHaveBeenCalledWith({ ignoreCache: true });
      // From the accounts page's refresh button, so it supersedes rather than joins.
      expect(mockRefreshBlockchainBalances).toHaveBeenCalledWith({ blockchain: Blockchain.ETH2 }, 'user');
    });
  });

  describe('confirmDelete', () => {
    it('should ask for confirmation for a single validator', () => {
      const item = validator();
      const { confirmDelete } = useEthValidatorOperations();
      confirmDelete(item);
      expect(mockShowConfirmation).toHaveBeenCalledWith({ data: [item], type: 'validator' });
    });
  });

  describe('deleteSelected', () => {
    it('should confirm deletion only for the selected validator indexes', () => {
      const rows = [validator({ index: 1 }), validator({ index: 2 }), validator({ index: 3 })];
      const { deleteSelected } = useEthValidatorOperations();
      deleteSelected(rows, [1, 3]);
      expect(mockShowConfirmation).toHaveBeenCalledWith({
        data: [rows[0], rows[2]],
        type: 'validator',
      });
    });
  });

  describe('accountOperation', () => {
    it('should be false when nothing is running', () => {
      const { accountOperation } = useEthValidatorOperations();
      expect(get(accountOperation)).toBe(false);
    });

    it.each([
      ['add account', mockAddRunning],
      ['remove account', mockRemoveRunning],
      ['section loading', mockLoading],
    ])('should be true while %s is active', (_label, flag) => {
      set(flag, true);
      const { accountOperation } = useEthValidatorOperations();
      expect(get(accountOperation)).toBe(true);
    });
  });
});
