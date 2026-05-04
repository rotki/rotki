import type { AccountManage, StakingValidatorManage } from './use-account-manage';
import type { ActionStatus } from '@/modules/core/common/action';
import { Blockchain } from '@rotki/common';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';

const mockAddAccounts = vi.fn();
const mockAddEvmAccounts = vi.fn();
const mockShowErrorMessage = vi.fn();

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn(() => ({
    addAccounts: mockAddAccounts,
    addEvmAccounts: mockAddEvmAccounts,
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    refreshAccounts: vi.fn().mockResolvedValue(undefined),
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/notifications/use-notifications')>(
    '@/modules/core/notifications/use-notifications',
  );
  return {
    ...actual,
    useNotifications: (): object => ({
      removeMatching: vi.fn(),
      showErrorMessage: mockShowErrorMessage,
      showSuccessMessage: vi.fn(),
    }),
  };
});

vi.mock('@/modules/accounts/use-blockchain-accounts', () => ({
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

vi.mock('@/modules/core/common/use-message-store', () => ({
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

  describe('saveAccount API validation errors', () => {
    function createSolanaAccountState(): AccountManage {
      return {
        chain: Blockchain.SOLANA,
        data: [{ address: 'Hasda78TSaT9bjiPxDBvP4GpohFpP3TDTaJEcCYK', tags: null }],
        mode: 'add',
        type: 'account',
      };
    }

    it('should map JSON-shaped api error message to inline form errors', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('{"address": ["Given value Hasda78TSaT9bjiPxDBvP4GpohFpP3TDTaJEcCYK is not a valid solana address"]}'));

      const { errorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(errorMessages)).toEqual({
        address: ['Given value Hasda78TSaT9bjiPxDBvP4GpohFpP3TDTaJEcCYK is not a valid solana address'],
      });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should fall back to a toast for non-JSON api errors', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('Network unreachable'));

      const { errorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(errorMessages)).toEqual({});
      expect(mockShowErrorMessage).toHaveBeenCalledWith(
        'account_form.error.title',
        expect.stringContaining('Network unreachable'),
      );
    });

    it('should fall back to a toast for empty-object JSON', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('{}'));

      const { errorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(errorMessages)).toEqual({});
      expect(mockShowErrorMessage).toHaveBeenCalledWith(
        'account_form.error.title',
        expect.stringContaining('{}'),
      );
    });

    it('should not double-parse an existing ApiValidationError', async () => {
      mockAddAccounts.mockRejectedValueOnce(new ApiValidationError('{"address": ["already typed"]}'));

      const { errorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(errorMessages)).toEqual({ address: ['already typed'] });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });
  });
});
