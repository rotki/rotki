import type { Ref } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify, Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType } from '@/modules/core/tasks/task-type';
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

vi.mock('@/modules/shell/sync-progress/use-section-status', () => ({
  useSectionStatus: (): { isLoading: Ref<boolean> } => ({ isLoading: mockLoading }),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: (): { useIsTaskRunning: (type: TaskType) => Ref<boolean> } => {
    const byType = new Map<TaskType, Ref<boolean>>([
      [TaskType.ADD_ACCOUNT, mockAddRunning],
      [TaskType.REMOVE_ACCOUNT, mockRemoveRunning],
    ]);
    return {
      useIsTaskRunning: (type: TaskType): Ref<boolean> => byType.get(type) ?? ref<boolean>(false),
    };
  },
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
      expect(mockRefreshBlockchainBalances).toHaveBeenCalledWith({ blockchain: Blockchain.ETH2 });
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
