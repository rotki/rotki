import type { Pinia } from 'pinia';
import type { AccountDataRow } from '../../types';
import type { BlockchainAccountGroupWithBalance, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountActions from '@/modules/accounts/table/components/table/AccountActions.vue';

const supportsTransactionsMock = vi.fn();

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    supportsTransactions: supportsTransactionsMock,
  })),
}));

describe('modules/accounts/table/components/table/AccountActions', () => {
  let wrapper: VueWrapper;
  let pinia: Pinia;

  const createAccountRow = (chain: string): AccountDataRow<BlockchainAccountWithBalance> => ({
    amount: bigNumberify('1'),
    category: undefined,
    chain,
    data: {
      address: '0x1234567890abcdef1234567890abcdef12345678',
      type: 'address',
    },
    expansion: undefined,
    groupHeader: false,
    groupId: undefined,
    id: `0x1234567890abcdef1234567890abcdef12345678#${chain}`,
    includedUsdValue: undefined,
    label: 'Test Account',
    nativeAsset: 'ETH',
    tags: [],
    type: 'account',
    usdValue: bigNumberify('1000'),
    virtual: false,
  });

  const createGroupRow = (chains: string[]): AccountDataRow<BlockchainAccountGroupWithBalance> => ({
    aggregatedAssets: [],
    allChains: chains,
    category: undefined,
    chains,
    data: {
      address: '0x1234567890abcdef1234567890abcdef12345678',
      type: 'address',
    },
    expansion: undefined,
    id: '0x1234567890abcdef1234567890abcdef12345678',
    includedUsdValue: undefined,
    label: 'Test Group',
    nativeAsset: undefined,
    tags: [],
    type: 'group',
    usdValue: bigNumberify('2000'),
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
    isOnlyShowingLoopringChain: boolean;
    isSectionLoading: boolean;
    isVirtual: boolean;
    row: AccountDataRow<BlockchainAccountWithBalance> | AccountDataRow<BlockchainAccountGroupWithBalance>;
  }): VueWrapper {
    return mount(AccountActions, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiButton: true,
          RuiIcon: true,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row: createAccountRow('btc'),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(false);
    });

    it('should show TokenDetection for groups with single chain that supports transactions', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row: createGroupRow(['eth']),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(true);
      expect(supportsTransactionsMock).toHaveBeenCalledWith('eth');
    });

    it('should hide TokenDetection for groups with multiple chains', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row: createGroupRow(['eth', 'optimism']),
      });

      expect(wrapper.findComponent({ name: 'TokenDetection' }).exists()).toBe(false);
    });
  });

  describe('rowActions visibility', () => {
    it('should show RowActions when not virtual and not only showing Loopring chain', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row: createAccountRow('eth'),
      });

      expect(wrapper.findComponent({ name: 'RowActions' }).exists()).toBe(true);
    });

    it('should hide RowActions when isVirtual is true', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: true,
        row: createAccountRow('eth'),
      });

      expect(wrapper.findComponent({ name: 'RowActions' }).exists()).toBe(false);
    });

    it('should hide RowActions when isOnlyShowingLoopringChain is true', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: true,
        isSectionLoading: false,
        isVirtual: false,
        row: createAccountRow('eth'),
      });

      expect(wrapper.findComponent({ name: 'RowActions' }).exists()).toBe(false);
    });
  });

  describe('rowActions edit button', () => {
    it('should show edit button when group is evm', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row,
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      await rowActions.vm.$emit('edit-click');

      const editEvents = wrapper.emitted('edit');
      expect(editEvents).toBeTruthy();
      expect(editEvents).toHaveLength(1);
      expect(editEvents![0]).toEqual(['evm', row]);
    });

    it('should emit delete event with correct parameters when delete button is clicked', async () => {
      supportsTransactionsMock.mockReturnValue(true);

      const row = createAccountRow('eth');
      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row,
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      await rowActions.vm.$emit('delete-click');

      const deleteEvents = wrapper.emitted('delete');
      expect(deleteEvents).toBeTruthy();
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
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
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row: createAccountRow('eth'),
      });

      const rowActions = wrapper.findComponent({ name: 'RowActions' });
      expect(rowActions.props('disabled')).toBe(false);
    });
  });

  describe('tokenDetection props', () => {
    it('should pass correct props to TokenDetection for account row', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: true,
        isVirtual: false,
        row: createAccountRow('eth'),
      });

      const tokenDetection = wrapper.findComponent({ name: 'TokenDetection' });
      expect(tokenDetection.props('address')).toBe('0x1234567890abcdef1234567890abcdef12345678');
      expect(tokenDetection.props('loading')).toBe(true);
      expect(tokenDetection.props('chain')).toBe('eth');
    });

    it('should pass correct chain prop to TokenDetection for group row with single chain', () => {
      supportsTransactionsMock.mockReturnValue(true);

      wrapper = createWrapper({
        accountOperation: false,
        group: 'evm',
        isOnlyShowingLoopringChain: false,
        isSectionLoading: false,
        isVirtual: false,
        row: createGroupRow(['optimism']),
      });

      const tokenDetection = wrapper.findComponent({ name: 'TokenDetection' });
      expect(tokenDetection.props('chain')).toBe('optimism');
    });
  });
});
