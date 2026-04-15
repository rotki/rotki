import type { StakingValidatorManage } from './use-account-manage';
import type { ValidationErrors } from '@/modules/api/types/errors';
import type { ActionStatus } from '@/modules/common/action';
import { Blockchain } from '@rotki/common';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn(() => ({
    addAccounts: vi.fn(),
    addEvmAccounts: vi.fn(),
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    refreshAccounts: vi.fn().mockResolvedValue(undefined),
  })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-api', () => ({
  useBlockchainAccounts: vi.fn(() => ({
    editAccount: vi.fn(),
    editAgnosticAccount: vi.fn(),
  })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({
    updateAccountData: vi.fn(),
    updateAccounts: vi.fn(),
  })),
}));

vi.mock('@/store/message', () => ({
  useMessageStore: vi.fn(() => ({
    setMessage: vi.fn(),
  })),
}));

const mockAddEth2Validator = vi.fn<() => Promise<ActionStatus<ValidationErrors | string>>>();
const mockEditEth2Validator = vi.fn<() => Promise<ActionStatus<ValidationErrors | string>>>();

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: vi.fn(() => ({
    addEth2Validator: mockAddEth2Validator,
    editEth2Validator: mockEditEth2Validator,
    updateEthStakingOwnership: vi.fn(),
  })),
}));

const { useAccountManage } = await import('./use-account-manage');

function createValidatorState(mode: 'add' | 'edit' = 'add'): StakingValidatorManage {
  return {
    chain: Blockchain.ETH2,
    data: {
      ownershipPercentage: mode === 'edit' ? '100' : undefined,
      publicKey: '0xabc123',
      validatorIndex: '12345',
    },
    mode,
    type: 'validator',
  };
}

describe('composables/accounts/blockchain/use-account-manage', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
  });

  describe('saveValidator', () => {
    it('should return true and clear errors on successful add', async () => {
      mockAddEth2Validator.mockResolvedValue({ success: true });

      const { save, saveError, saveErrorIsPremium } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(true);
      expect(get(saveError)).toBe('');
      expect(get(saveErrorIsPremium)).toBe(false);
    });

    it('should set saveError on failure with string message', async () => {
      mockAddEth2Validator.mockResolvedValue({
        message: 'Querying https://beaconcha.in/api/v1/validator failed due to missing API key',
        success: false,
      });

      const { save, saveError, saveErrorIsPremium } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(false);
      expect(get(saveError)).toBe('Querying https://beaconcha.in/api/v1/validator failed due to missing API key');
      expect(get(saveErrorIsPremium)).toBe(false);
    });

    it('should set saveErrorIsPremium when error contains limit exceeded', async () => {
      mockAddEth2Validator.mockResolvedValue({
        message: 'ETH staking limit exceeded. Current staked: 38.785 ETH, limit: 128 ETH. Would be: 277.278 ETH',
        success: false,
      });

      const { save, saveError, saveErrorIsPremium } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(false);
      expect(get(saveError)).toContain('limit exceeded');
      expect(get(saveErrorIsPremium)).toBe(true);
    });

    it('should set errorMessages on failure with validation errors', async () => {
      const validationErrors: ValidationErrors = {
        publicKey: ['Invalid public key format'],
      };
      mockAddEth2Validator.mockResolvedValue({
        message: validationErrors,
        success: false,
      });

      const { errorMessages, save, saveError } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(false);
      expect(get(errorMessages)).toEqual(validationErrors);
      expect(get(saveError)).toBe('');
    });

    it('should clear saveError before each save attempt', async () => {
      mockAddEth2Validator
        .mockResolvedValueOnce({
          message: 'First error',
          success: false,
        })
        .mockResolvedValueOnce({
          success: true,
        });

      const { save, saveError } = useAccountManage();

      await save(createValidatorState());
      expect(get(saveError)).toBe('First error');

      await save(createValidatorState());
      expect(get(saveError)).toBe('');
    });

    it('should clear saveErrorIsPremium before each save attempt', async () => {
      mockAddEth2Validator
        .mockResolvedValueOnce({
          message: 'ETH staking limit exceeded',
          success: false,
        })
        .mockResolvedValueOnce({
          message: 'Some other error',
          success: false,
        });

      const { save, saveErrorIsPremium } = useAccountManage();

      await save(createValidatorState());
      expect(get(saveErrorIsPremium)).toBe(true);

      await save(createValidatorState());
      expect(get(saveErrorIsPremium)).toBe(false);
    });

    it('should use editEth2Validator for edit mode', async () => {
      mockEditEth2Validator.mockResolvedValue({ success: true });

      const { save } = useAccountManage();
      const state = createValidatorState('edit');

      await save(state);

      expect(mockEditEth2Validator).toHaveBeenCalledWith(state.data);
      expect(mockAddEth2Validator).not.toHaveBeenCalled();
    });

    it('should set pending during save', async () => {
      let resolvePromise: (value: ActionStatus<ValidationErrors | string>) => void;
      mockAddEth2Validator.mockImplementation(async () => new Promise((resolve) => {
        resolvePromise = resolve;
      }));

      const { pending, save } = useAccountManage();
      expect(get(pending)).toBe(false);

      const savePromise = save(createValidatorState());
      expect(get(pending)).toBe(true);

      resolvePromise!({ success: true });
      await savePromise;
      expect(get(pending)).toBe(false);
    });
  });
});
