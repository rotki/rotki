import type { AccountManage, StakingValidatorManage } from './use-account-manage';
import type { ActionStatus } from '@/modules/core/common/action';
import { Blockchain, Zero } from '@rotki/common';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type BlockchainAccountBalance, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
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

// Mocked outright rather than spread over `...actual`: importActual evaluates the real
// notifications graph, which costs ~1.2s to import.
// `getErrorMessage` is a pure helper re-exported from a light module, so take it from there.
vi.mock('@/modules/core/notifications/use-notifications', async () => ({
  getErrorMessage: (await vi.importActual<typeof import('@/modules/core/common/logging/error-handling')>(
    '@/modules/core/common/logging/error-handling',
  )).getErrorMessage,
  useNotifications: (): object => ({
    removeMatching: vi.fn(),
    showErrorMessage: mockShowErrorMessage,
    showSuccessMessage: vi.fn(),
  }),
}));

vi.mock('@/modules/accounts/use-account-edits', () => ({
  useAccountEdits: vi.fn(() => ({
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

const { editBlockchainAccount, useAccountManage } = await import('./use-account-manage');

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

    it('should translate the missing api key error to a friendly message', async () => {
      mockAddEth2Validator.mockResolvedValue({
        message: 'Querying https://beaconcha.in/api/v1/validator failed due to missing API key',
        success: false,
      });

      const { save, saveError, saveErrorIsPremium } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(false);
      expect(get(saveError)).toBe('account_form.error.validator_needs_credentials');
      expect(get(saveErrorIsPremium)).toBe(false);
    });

    it('should set saveError on failure with string message', async () => {
      mockAddEth2Validator.mockResolvedValue({
        message: 'Some other backend failure',
        success: false,
      });

      const { save, saveError, saveErrorIsPremium } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(false);
      expect(get(saveError)).toBe('Some other backend failure');
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

    it('should set modelErrorMessages on failure with validation errors', async () => {
      const validationErrors: ValidationErrors = {
        publicKey: ['Invalid public key format'],
      };
      mockAddEth2Validator.mockResolvedValue({
        message: validationErrors,
        success: false,
      });

      const { modelErrorMessages, save, saveError } = useAccountManage();
      const result = await save(createValidatorState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual(validationErrors);
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

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({
        address: ['Given value Hasda78TSaT9bjiPxDBvP4GpohFpP3TDTaJEcCYK is not a valid solana address'],
      });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should fall back to a toast for non-JSON api errors', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('Network unreachable'));

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).toHaveBeenCalledWith(
        'account_form.error.title',
        expect.stringContaining('Network unreachable'),
      );
    });

    it('should fall back to a toast for empty-object JSON', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('{}'));

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).toHaveBeenCalledWith(
        'account_form.error.title',
        expect.stringContaining('{}'),
      );
    });

    it('should not double-parse an existing ApiValidationError', async () => {
      mockAddAccounts.mockRejectedValueOnce(new ApiValidationError('{"address": ["already typed"]}'));

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createSolanaAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({ address: ['already typed'] });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });
  });

  describe('editBlockchainAccount', () => {
    it('should build a validator edit state from validator data', () => {
      const account: BlockchainAccountBalance = {
        amount: Zero,
        chain: Blockchain.ETH2,
        data: { index: 12345, ownershipPercentage: '50', publicKey: '0xabc', status: 'active', type: 'validator' },
        label: 'My validator',
        nativeAsset: 'ETH',
        type: 'account',
        value: Zero,
      };

      expect(editBlockchainAccount(account)).toEqual({
        chain: Blockchain.ETH2,
        data: { ownershipPercentage: '50', publicKey: '0xabc', validatorIndex: '12345' },
        mode: 'edit',
        type: 'validator',
      });
    });

    it('should default the validator ownership to 100 when missing', () => {
      const account: BlockchainAccountBalance = {
        amount: Zero,
        chain: Blockchain.ETH2,
        data: { index: 7, publicKey: '0xdef', status: 'active', type: 'validator' },
        nativeAsset: 'ETH',
        type: 'account',
        value: Zero,
      };

      expect(editBlockchainAccount(account)).toMatchObject({
        data: { ownershipPercentage: '100', validatorIndex: '7' },
        type: 'validator',
      });
    });

    it('should build an xpub edit state from xpub data', () => {
      const account: BlockchainAccountBalance = {
        amount: Zero,
        chain: Blockchain.BTC,
        data: { derivationPath: 'm/0', type: 'xpub', xpub: 'xpubSomeKey' },
        label: 'My xpub',
        nativeAsset: 'BTC',
        tags: ['cold'],
        type: 'account',
        value: Zero,
      };

      expect(editBlockchainAccount(account)).toEqual({
        chain: Blockchain.BTC,
        data: {
          label: 'My xpub',
          tags: ['cold'],
          xpub: { derivationPath: 'm/0', xpub: 'xpubSomeKey', xpubType: XpubKeyType.XPUB },
        },
        mode: 'edit',
        type: 'xpub',
      });
    });

    it('should build an agnostic group edit state for multi-chain groups', () => {
      const account: BlockchainAccountBalance = {
        category: 'evm',
        chains: [Blockchain.ETH, Blockchain.OPTIMISM],
        data: { address: '0xADDRESS', type: 'address' },
        label: '0xADDRESS',
        type: 'group',
        value: Zero,
      };

      expect(editBlockchainAccount(account)).toEqual({
        category: 'evm',
        chain: undefined,
        data: { address: '0xADDRESS', label: undefined, tags: null },
        mode: 'edit',
        type: 'group',
      });
    });

    it('should build a single-account edit state and keep a distinct label', () => {
      const account: BlockchainAccountBalance = {
        amount: Zero,
        chain: Blockchain.ETH,
        data: { address: '0xABC', type: 'address' },
        label: 'Main wallet',
        nativeAsset: 'ETH',
        tags: ['hot'],
        type: 'account',
        value: Zero,
      };

      expect(editBlockchainAccount(account)).toEqual({
        chain: Blockchain.ETH,
        data: { address: '0xABC', label: 'Main wallet', tags: ['hot'] },
        mode: 'edit',
        type: 'account',
      });
    });
  });
});
