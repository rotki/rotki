import type { Pinia } from 'pinia';
import type { AccountDataRow } from '../../types';
import type {
  AddressAccount,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountWithBalance,
  ValidatorAccount,
} from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { getAccountGroupId, getAccountId, getGroupId } from '@/modules/accounts/account-utils';
import { createAccount, createValidatorAccount } from '@/modules/accounts/create-account';
import AccountActions from '@/modules/accounts/table/components/table/AccountActions.vue';

const supportsTransactionsMock = vi.fn();

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    supportsTransactions: supportsTransactionsMock,
  })),
}));

vi.mock('@/modules/accounts/blockchain/use-account-delete', () => ({
  useAccountDelete: vi.fn(() => ({
    describeDeletion: (): string => 'what deleting removes',
  })),
}));

describe('modules/accounts/table/components/table/AccountActions', () => {
  let wrapper: VueWrapper;
  let pinia: Pinia;

  const ADDRESS = '0x1234567890abcdef1234567890abcdef12345678';

  const toAccountRow = (account: AddressAccount | ValidatorAccount): AccountDataRow<BlockchainAccountWithBalance> => ({
    ...account,
    amount: bigNumberify('1'),
    expansion: undefined,
    groupId: getAccountGroupId(account),
    id: getAccountId(account),
    includedValue: undefined,
    label: 'Test Account',
    tags: [],
    type: 'account',
    value: bigNumberify('1000'),
  });

  const createAccountRow = (chain: string): AccountDataRow<BlockchainAccountWithBalance> =>
    toAccountRow(createAccount({ address: ADDRESS, label: null, tags: null }, chain));

  const createGroupRow = (chains: string[]): AccountDataRow<BlockchainAccountGroupWithBalance> => ({
    address: ADDRESS,
    allChains: chains,
    category: 'evm',
    chains,
    expansion: undefined,
    id: getGroupId({ address: ADDRESS, chains, kind: 'address' }),
    includedValue: undefined,
    kind: 'address',
    label: 'Test Group',
    tags: [],
    type: 'group',
    value: bigNumberify('2000'),
  });

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    supportsTransactionsMock.mockReset();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  function createWrapper(props: {
    accountOperation: boolean;
    group?: 'evm' | 'xpub';
    isSectionLoading: boolean;
    row: AccountDataRow<BlockchainAccountWithBalance> | AccountDataRow<BlockchainAccountGroupWithBalance>;
  }): VueWrapper {
    return mount(AccountActions, {
      global: {
        plugins: [pinia],
        stubs: {
          AccountSkipQueriesToggle: true,
          RuiButton: true,
          RuiIcon: true,
          // the row's upkeep sits in a menu; rendered open here so its entries can be inspected
          RuiMenu: { template: '<div><slot name="activator" v-bind="{ attrs: {} }" /><slot /></div>' },
          RuiProgress: true,
          RuiTooltip: true,
          TokenDetection: true,
        },
      },
      props,
    });
  }

  describe('rendering', () => {
    it('should render the component correctly', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      expect(wrapper.exists()).toBe(true);
    });
  });

  describe('tokenDetection visibility', () => {
    it('should show TokenDetection for accounts that support transactions', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(true);
      expect(supportsTransactionsMock).toHaveBeenCalledWith('eth');
    });

    it('should hide TokenDetection for accounts that do not support transactions', () => {
      supportsTransactionsMock.mockReturnValue(false);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('btc'),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(false);
    });

    it('should show TokenDetection for groups with single chain that supports transactions', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createGroupRow(['eth']),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(true);
      expect(supportsTransactionsMock).toHaveBeenCalledWith('eth');
    });

    it('should show TokenDetection for groups with multiple chains if at least one supports transactions', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createGroupRow(['eth', 'optimism']),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(true);
    });

    it('should hide TokenDetection for groups with multiple chains if none support transactions', () => {
      supportsTransactionsMock.mockReturnValue(false);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createGroupRow(['btc', 'bch']),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(false);
    });
  });

  describe('rowActions edit button', () => {
    it('should show edit button when group is evm', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      expect(rowActions.props('noEdit')).toBe(false);
    });

    it('should hide edit button when group is not evm', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'xpub',
        isSectionLoading: false,
        row: createAccountRow('btc'),
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      expect(rowActions.props('noEdit')).toBe(true);
    });

    it('should hide edit button when group is undefined', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: undefined,
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      expect(rowActions.props('noEdit')).toBe(true);
    });
  });

  describe('events', () => {
    it('should emit edit event with correct parameters when edit button is clicked', async () => {
      supportsTransactionsMock.mockReturnValue(true);

      const row = createAccountRow('eth');
      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row,
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      await rowActions.vm.$emit('edit-click');

      const editEvents = wrapper.emitted('edit');
      expect(editEvents).toBeDefined();
      expect(editEvents).toHaveLength(1);
      expect(editEvents![0]).toEqual(['evm', row]);
    });

    it('should emit delete event with correct parameters when delete button is clicked', async () => {
      supportsTransactionsMock.mockReturnValue(true);

      const row = createAccountRow('eth');
      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row,
      });

      const button = (testId: string): VueWrapper | undefined => wrapper.findAllComponents({ name: 'RuiButton' })
        .find(candidate => candidate.attributes('data-testid') === testId);

      // the first click only asks, inline in the menu, saying what the delete removes
      button('row-delete')!.vm.$emit('click');
      await nextTick();
      expect(wrapper.emitted('delete')).toBeUndefined();
      expect(wrapper.find('[data-testid=row-delete-confirm]').text()).toContain('what deleting removes');

      button('row-delete-confirm-run')!.vm.$emit('click');
      await nextTick();

      const deleteEvents = wrapper.emitted('delete');
      expect(deleteEvents).toBeDefined();
      expect(deleteEvents).toHaveLength(1);
      expect(deleteEvents![0]).toEqual([row]);
    });
  });

  describe('disabled state', () => {
    it('should pass disabled prop to RowActions when accountOperation is true', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: true,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      expect(rowActions.props('disabled')).toBe(true);
    });

    it('should pass disabled as false to RowActions when accountOperation is false', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      expect(rowActions.props('disabled')).toBe(false);
    });
  });

  describe('skip queries toggle', () => {
    beforeEach(() => {
      supportsTransactionsMock.mockReturnValue(true);
    });

    it('should scope it to every chain the group stands for', () => {
      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createGroupRow(['eth', 'optimism', 'base']),
      });

      const toggle = wrapper.findComponent({ name: 'AccountSkipQueriesToggle' });
      expect(toggle.props('chains')).toEqual(['eth', 'optimism', 'base']);
      expect(toggle.props('address')).toBe('0x1234567890abcdef1234567890abcdef12345678');
    });

    it('should scope it to the one chain of an account row', () => {
      wrapper = createWrapper({
        accountOperation: false,
        isSectionLoading: false,
        row: createAccountRow('optimism'),
      });

      expect(wrapper.findComponent({ name: 'AccountSkipQueriesToggle' }).props('chains')).toEqual(['optimism']);
    });

    it('should hide it for a validator, whose public key no rule matches', () => {
      const row = toAccountRow(createValidatorAccount({
        index: 1,
        publicKey: '0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c',
        status: 'active',
      }, 'eth2'));

      wrapper = createWrapper({
        accountOperation: false,
        isSectionLoading: false,
        row,
      });

      expect(wrapper.findComponent({ name: 'AccountSkipQueriesToggle' }).exists()).toBe(false);
    });

    it('should disable it while an account operation is running', () => {
      wrapper = createWrapper({
        accountOperation: true,
        group: 'evm',
        isSectionLoading: false,
        row: createAccountRow('eth'),
      });

      expect(wrapper.findComponent({ name: 'AccountSkipQueriesToggle' }).props('disabled')).toBe(true);
    });
  });

  describe('tokenDetection props', () => {
    it('should pass correct props to TokenDetection for account row', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: true,
        row: createAccountRow('eth'),
      });

      const tokenDetection = wrapper.findComponent({ name: 'TokenDetection' });
      expect(tokenDetection.props('address')).toBe('0x1234567890abcdef1234567890abcdef12345678');
      expect(tokenDetection.props('loading')).toBe(true);
      expect(tokenDetection.props('chains')).toEqual(['eth']);
    });

    it('should pass correct chains prop to TokenDetection for group row with single chain', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createGroupRow(['optimism']),
      });

      const tokenDetection = wrapper.findComponent({ name: 'TokenDetection' });
      expect(tokenDetection.props('chains')).toEqual(['optimism']);
    });

    it('should pass only supported chains to TokenDetection for group row with multiple chains', () => {
      supportsTransactionsMock.mockImplementation((chain: string) => chain === 'eth' || chain === 'optimism');

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isSectionLoading: false,
        row: createGroupRow(['eth', 'optimism', 'btc']),
      });

      const tokenDetection = wrapper.findComponent({ name: 'TokenDetection' });
      expect(tokenDetection.props('chains')).toEqual(['eth', 'optimism']);
    });
  });
});
