import type { AccountAgnosticManage, AccountManage, StakingValidatorManage, XpubManage } from './use-account-manage';
import type { ActionStatus } from '@/modules/core/common/action';
import { bigNumberify, Blockchain, Zero } from '@rotki/common';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getAccountGroupId } from '@/modules/accounts/account-utils';
import { ALL_EVM_CHAINS, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { type BlockchainAccountBalance, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { createAccount, createValidatorAccount } from '@/modules/accounts/create-account';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const mockAddAccounts = vi.fn();
const mockShowErrorMessage = vi.fn();
const mockFetchAccounts = vi.fn().mockResolvedValue(undefined);
const mockRefreshAccounts = vi.fn().mockResolvedValue(undefined);
const mockUpdateEthStakingOwnership = vi.fn();
const mockEditAccount = vi.fn();
const mockEditAgnosticAccount = vi.fn();
const mockUpdateAccountData = vi.fn();
const mockUpdateAccounts = vi.fn();

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn(() => ({
    addAccounts: mockAddAccounts,
    fetchAccounts: mockFetchAccounts,
    refreshAccounts: mockRefreshAccounts,
  })),
}));

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
    editAccount: mockEditAccount,
    editAgnosticAccount: mockEditAgnosticAccount,
  })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({
    updateAccountData: mockUpdateAccountData,
    updateAccounts: mockUpdateAccounts,
  })),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: vi.fn(() => ({
    setMessage: vi.fn(),
  })),
}));

const mockIsEvmCompatible = vi.fn<(chain: string) => boolean>();

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    isEvmCompatible: mockIsEvmCompatible,
  })),
}));

const mockAddEth2Validator = vi.fn<() => Promise<ActionStatus<ValidationErrors | string>>>();
const mockEditEth2Validator = vi.fn<() => Promise<ActionStatus<ValidationErrors | string>>>();

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: vi.fn(() => ({
    addEth2Validator: mockAddEth2Validator,
    editEth2Validator: mockEditEth2Validator,
    updateEthStakingOwnership: mockUpdateEthStakingOwnership,
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
    mockIsEvmCompatible.mockImplementation(chain => chain === Blockchain.ETH || chain === Blockchain.ZKSYNC_LITE);
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

    it('should refresh the eth2 accounts after an add, leaving ownership alone', async () => {
      mockAddEth2Validator.mockResolvedValue({ success: true });

      const { save } = useAccountManage();
      await save(createValidatorState());

      expect(mockRefreshAccounts).toHaveBeenCalledWith({ blockchain: Blockchain.ETH2 });
      expect(mockFetchAccounts).not.toHaveBeenCalled();
      expect(mockUpdateEthStakingOwnership).not.toHaveBeenCalled();
    });

    it('should update the ownership and re-read the eth2 accounts after an edit', async () => {
      mockEditEth2Validator.mockResolvedValue({ success: true });

      const { save } = useAccountManage();
      await save(createValidatorState('edit'));

      expect(mockUpdateEthStakingOwnership).toHaveBeenCalledWith('0xabc123', bigNumberify('100'));
      expect(mockFetchAccounts).toHaveBeenCalledWith({ blockchain: Blockchain.ETH2 });
      expect(mockRefreshAccounts).not.toHaveBeenCalled();
    });

    it('should refresh nothing when the backend refuses the validator', async () => {
      mockAddEth2Validator.mockResolvedValue({ message: 'refused', success: false });

      const { save } = useAccountManage();
      await save(createValidatorState());

      expect(mockRefreshAccounts).not.toHaveBeenCalled();
      expect(mockFetchAccounts).not.toHaveBeenCalled();
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

  describe('saveAccount for an ENS name, which waits for the addition', () => {
    function createEnsAccountState(): AccountManage {
      return {
        chain: Blockchain.ETH,
        data: [{ address: 'rotki.eth', tags: null }],
        mode: 'add',
        type: 'account',
      };
    }

    it('should map JSON-shaped api error message to inline form errors', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('{"address": ["Given ENS address rotki.eth could not be resolved"]}'));

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createEnsAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({
        address: ['Given ENS address rotki.eth could not be resolved'],
      });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should fall back to a toast for non-JSON api errors', async () => {
      mockAddAccounts.mockRejectedValueOnce(new Error('Network unreachable'));

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createEnsAccountState());

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
      const result = await save(createEnsAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).toHaveBeenCalledWith(
        'account_form.error.title',
        expect.stringContaining('{}'),
      );
    });

    it('should map a resolved failure cause to inline form errors', async () => {
      mockAddAccounts.mockResolvedValueOnce({
        added: [],
        cancelled: false,
        failed: [{
          account: { address: 'rotki.eth', tags: null },
          error: TaskFailed({
            cause: new ApiValidationError('{"address": ["Given ENS address rotki.eth could not be resolved"]}'),
            message: 'validation failed',
          }),
        }],
      });

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createEnsAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({
        address: ['Given ENS address rotki.eth could not be resolved'],
      });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should report the count when several addresses fail', async () => {
      mockAddAccounts.mockResolvedValueOnce({
        added: [],
        cancelled: false,
        failed: [
          {
            account: { address: '0xone', tags: null },
            error: TaskFailed({ cause: new ApiValidationError('{"address": ["bad"]}'), message: 'validation failed' }),
          },
          {
            account: { address: '0xtwo', tags: null },
            error: TaskFailed({ message: 'boom' }),
          },
        ],
      });

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createEnsAccountState());

      expect(result).toBe(false);
      // No single field to highlight across two addresses.
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).toHaveBeenCalledWith(
        'account_form.error.title',
        expect.stringContaining('account_form.error.addition_failed'),
      );
    });

    it('should not report a fully cancelled addition as saved, which would close the dialog and emit complete for an account never added', async () => {
      mockAddAccounts.mockResolvedValueOnce({ added: [], cancelled: true, failed: [], skipped: 0 });

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createEnsAccountState());

      expect(result).toBe(false);
      // The user asked for the cancellation, so nothing is reported.
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should close on a skipped address without an error, leaving the dock to say why', async () => {
      mockAddAccounts.mockResolvedValueOnce({ added: [], cancelled: false, failed: [], skipped: 1 });

      const { modelErrorMessages, save } = useAccountManage();

      expect(await save(createEnsAccountState())).toBe(true);
      expect(mockAddAccounts).toHaveBeenCalledWith(expect.any(String), expect.anything(), { userStarted: true, wait: true });
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should not double-parse an existing ApiValidationError', async () => {
      mockAddAccounts.mockRejectedValueOnce(new ApiValidationError('{"address": ["already typed"]}'));

      const { modelErrorMessages, save } = useAccountManage();
      const result = await save(createEnsAccountState());

      expect(result).toBe(false);
      expect(get(modelErrorMessages)).toEqual({ address: ['already typed'] });
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });
  });

  describe('saveAccount for well-formed hex addresses, which closes on submit', () => {
    const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

    function createAddressState(addresses: string[], chain: string = Blockchain.ETH): AccountManage {
      return {
        chain,
        data: addresses.map(address => ({ address, tags: null })),
        mode: 'add',
        type: 'account',
      };
    }

    it('should close without waiting for the addition, leaving the dock to report it', async () => {
      mockAddAccounts.mockResolvedValueOnce({ added: [], cancelled: false, failed: [], skipped: 0 });

      const { modelErrorMessages, save } = useAccountManage();

      expect(await save(createAddressState([address]))).toBe(true);
      expect(mockAddAccounts).toHaveBeenCalledWith(Blockchain.ETH, expect.anything(), { userStarted: true, wait: false });
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });

    it('should close without waiting when adding to every evm chain', async () => {
      mockAddAccounts.mockResolvedValueOnce({ added: [], cancelled: false, failed: [], skipped: 0 });

      const { save } = useAccountManage();

      expect(await save(createAddressState([address], ALL_EVM_CHAINS))).toBe(true);
      expect(mockAddAccounts).toHaveBeenCalledWith(EVM_PSEUDO_CHAIN, expect.anything(), { userStarted: true, wait: false });
    });

    it('should close without waiting on an evm-like chain', async () => {
      mockAddAccounts.mockResolvedValueOnce({ added: [], cancelled: false, failed: [], skipped: 0 });

      const { save } = useAccountManage();

      expect(await save(createAddressState([address], Blockchain.ZKSYNC_LITE))).toBe(true);
      expect(mockAddAccounts).toHaveBeenCalledWith(Blockchain.ZKSYNC_LITE, expect.anything(), { userStarted: true, wait: false });
    });

    it('should wait while the supported chains are not known yet', async () => {
      mockIsEvmCompatible.mockReturnValue(false);
      mockAddAccounts.mockResolvedValueOnce({ added: [], cancelled: false, failed: [], skipped: 0 });

      const { save } = useAccountManage();
      await save(createAddressState([address]));

      expect(mockAddAccounts).toHaveBeenCalledWith(Blockchain.ETH, expect.anything(), { userStarted: true, wait: true });
    });

    it.each([
      ['a mistyped hex address', [address.slice(0, -1)], Blockchain.ETH],
      ['a batch holding an ENS name', [address, 'rotki.eth'], Blockchain.ETH],
      ['an address on a chain that takes no hex', ['bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq'], Blockchain.BTC],
    ])('should wait for %s, so a rejection stays on the form', async (_, addresses, chain) => {
      mockAddAccounts.mockResolvedValueOnce({
        added: [],
        cancelled: false,
        failed: [{
          account: { address: addresses[0], tags: null },
          error: TaskFailed({ cause: new ApiValidationError('{"address": ["not an address"]}'), message: 'validation failed' }),
        }],
      });

      const { modelErrorMessages, save } = useAccountManage();

      expect(await save(createAddressState(addresses, chain))).toBe(false);
      expect(mockAddAccounts).toHaveBeenCalledWith(chain, expect.anything(), { userStarted: true, wait: true });
      expect(get(modelErrorMessages)).toEqual({ address: ['not an address'] });
    });
  });

  describe('saveXpub', () => {
    function xpubState(mode: 'add' | 'edit'): XpubManage {
      return {
        chain: Blockchain.BTC,
        data: {
          tags: null,
          xpub: { derivationPath: 'm/0', xpub: 'zpub6r', xpubType: XpubKeyType.ZPUB },
        },
        mode,
        type: 'xpub',
      };
    }

    it('should add the xpub and report it saved', async () => {
      mockAddAccounts.mockResolvedValue({ added: [{ address: 'zpub6r' }], failed: [], noActivity: [] });

      const { save } = useAccountManage();

      expect(await save(xpubState('add'))).toBe(true);
      expect(mockAddAccounts).toHaveBeenCalledWith(Blockchain.BTC, xpubState('add').data, { userStarted: true, wait: true });
    });

    /** An edit does not go through the addition summary, so the list is re-read instead. */
    it('should edit the xpub and re-read the chain', async () => {
      const { save } = useAccountManage();

      expect(await save(xpubState('edit'))).toBe(true);
      expect(mockEditAccount).toHaveBeenCalledWith(xpubState('edit').data, Blockchain.BTC);
      expect(mockFetchAccounts).toHaveBeenCalledWith({ blockchain: Blockchain.BTC });
    });

    /**
     * The xpub errors are reported against the two fields of the xpub form rather than an address,
     * which is what the empty props name.
     */
    it('should report a failed addition against the xpub fields', async () => {
      mockAddAccounts.mockResolvedValue({
        added: [],
        failed: [{ address: 'zpub6r', error: new Error('{"xpub":["not a valid xpub"]}') }],
        noActivity: [],
      });

      const { modelErrorMessages, save } = useAccountManage();

      expect(await save(xpubState('add'))).toBe(false);
      expect(get(modelErrorMessages)).toEqual({ xpub: ['not a valid xpub'] });
    });

    it('should report a rejected edit rather than closing the dialog', async () => {
      mockEditAccount.mockRejectedValue(new Error('the backend said no'));

      const { save } = useAccountManage();

      expect(await save(xpubState('edit'))).toBe(false);
      expect(mockShowErrorMessage).toHaveBeenCalled();
    });

    /** Cancelling the addition is not a failure, but nothing was added, so the dialog stays open. */
    it('should not report a fully cancelled addition as saved', async () => {
      mockAddAccounts.mockResolvedValue({ added: [], cancelled: true, failed: [], skipped: 0 });

      const { modelErrorMessages, save } = useAccountManage();

      expect(await save(xpubState('add'))).toBe(false);
      expect(get(modelErrorMessages)).toEqual({});
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
    });
  });

  describe('saveAgnosticAccount', () => {
    function groupState(): AccountAgnosticManage {
      return {
        category: 'evm',
        chain: undefined,
        data: { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null },
        mode: 'edit',
        type: 'group',
      };
    }

    /** A group spans chains, so the edit is written once and mirrored into every account. */
    it('should edit the group and carry the change into the accounts', async () => {
      const { save } = useAccountManage();

      expect(await save(groupState())).toBe(true);
      expect(mockEditAgnosticAccount).toHaveBeenCalledWith('evm', groupState().data);
      expect(mockUpdateAccountData).toHaveBeenCalledWith(groupState().data);
    });

    it('should not touch the accounts when the edit is rejected', async () => {
      mockEditAgnosticAccount.mockRejectedValue(new Error('the backend said no'));

      const { save } = useAccountManage();

      expect(await save(groupState())).toBe(false);
      expect(mockUpdateAccountData).not.toHaveBeenCalled();
    });
  });

  describe('editBlockchainAccount', () => {
    it('should build a validator edit state from validator data', () => {
      const validator = createValidatorAccount({ index: 12345, ownershipPercentage: '50', publicKey: '0xabc', status: 'active' }, Blockchain.ETH2);
      const account: BlockchainAccountBalance = {
        ...validator,
        amount: Zero,
        groupId: getAccountGroupId(validator),
        label: 'My validator',
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
      const validator = createValidatorAccount({ index: 7, publicKey: '0xdef', status: 'active' }, Blockchain.ETH2);
      const account: BlockchainAccountBalance = {
        ...validator,
        amount: Zero,
        groupId: getAccountGroupId(validator),
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
        category: 'bitcoin',
        chains: [Blockchain.BTC],
        derivationPath: 'm/0',
        kind: 'xpub',
        label: 'My xpub',
        nativeAsset: 'BTC',
        tags: ['cold'],
        type: 'group',
        value: Zero,
        xpub: 'xpubSomeKey',
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
        address: '0xADDRESS',
        category: 'evm',
        chains: [Blockchain.ETH, Blockchain.OPTIMISM],
        kind: 'address',
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
      const address = createAccount({ address: '0xABC', label: 'Main wallet', tags: ['hot'] }, Blockchain.ETH);
      const account: BlockchainAccountBalance = {
        ...address,
        amount: Zero,
        groupId: getAccountGroupId(address),
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
