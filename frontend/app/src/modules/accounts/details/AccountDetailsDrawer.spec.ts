import type { AccountDetailsView } from '@/modules/accounts/details/account-details-views';
import type { AccountDetailsOpenMode } from '@/modules/accounts/details/use-account-details-route';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountKind, type BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import AccountDetailsDrawer from '@/modules/accounts/details/AccountDetailsDrawer.vue';
import { DRAWER_SLIDE_MS } from '@/modules/accounts/details/use-drawer-presence';

const { accountId, assetsMounted, close, discard, groups, open, setView, settled, view } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    accountId: ref<string | undefined>(),
    assetsMounted: vi.fn<() => void>(),
    close: vi.fn<() => Promise<void>>(async () => {}),
    discard: vi.fn<() => Promise<void>>(async () => {}),
    groups: ref<BlockchainAccountGroupWithBalance[]>([]),
    open: vi.fn<(id: string, mode: AccountDetailsOpenMode) => Promise<void>>(async () => {}),
    setView: vi.fn<(next: AccountDetailsView) => Promise<void>>(async () => {}),
    settled: ref<boolean>(true),
    view: ref<AccountDetailsView | undefined>(),
  };
});

vi.mock('@/modules/accounts/details/use-account-details-route', () => ({
  useAccountDetailsRoute: (): object => ({ accountId, close, discard, open, setView, view }),
}));

vi.mock('@/modules/accounts/use-account-category-helper', async () => {
  const { computed } = await import('vue');
  return { useAccountCategoryHelper: (): object => ({ chainIds: computed<string[]>(() => ['eth', 'optimism']) }) };
});

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: (): object => ({ isChainSettled: (): boolean => get(settled) }),
}));

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', () => ({
  useBlockchainAccountData: (): object => ({ getAccountsByCategory: (): unknown => groups }),
}));

const stubs = {
  AccountDetailsAssets: {
    mounted(): void {
      assetsMounted();
    },
    props: { chains: Array, groupId: String, searchable: Boolean },
    template: '<div data-testid="assets-stub" :data-chains="chains.join(\',\')" :data-searchable="String(searchable)" tabindex="0" />',
  },
  AccountDetailsChainSection: { props: ['chain', 'groupId'], template: '<div data-testid="chain-section-stub" :data-chain="chain" />' },
  AccountDetailsHeader: {
    emits: ['close'],
    methods: { focusClose(): void {} },
    template: '<button data-testid="account-details-close" @click="$emit(\'close\')" />',
  },
  AccountGroupDetailsTable: { props: ['groupId', 'chains'], template: '<div data-testid="table-stub" :data-group="groupId" :data-chains="chains.join(\',\')" />' },
  RuiNavigationDrawer: {
    emits: ['closed', 'update:modelValue'],
    props: ['modelValue'],
    template: '<div data-testid="drawer" :data-open="String(modelValue)"><button data-testid="scrim" @click="$emit(\'update:modelValue\', false)" /><button data-testid="slid-out" @click="$emit(\'closed\')" /><slot /></div>',
  },
  RuiTab: { template: '<span><slot /></span>' },
  RuiTabs: {
    emits: ['update:modelValue'],
    name: 'RuiTabs',
    props: ['modelValue'],
    template: '<div data-testid="tabs" :data-index="modelValue"><slot /></div>',
  },
};

function address(id: string, chains: string[]): BlockchainAccountGroupWithBalance {
  return createMock<BlockchainAccountGroupWithBalance>({ address: id, chains, expansion: chains.length > 1 ? 'accounts' : 'assets', kind: AccountKind.ADDRESS });
}

function createWrapper(
  chainExclusionFilter: Record<string, string[]> = {},
  options: { slots?: Record<string, string>; selectionMode?: boolean } = {},
): VueWrapper<InstanceType<typeof AccountDetailsDrawer>> {
  const { selectionMode = false, slots = {} } = options;
  return mount(AccountDetailsDrawer, {
    global: { stubs },
    props: { category: 'evm', chainExclusionFilter, selectedAssets: undefined, selectionMode, visibleTags: [] },
    slots,
  });
}

/** Mounts the drawer and lets its slide in finish, so its lists are mounted. */
async function createSlidIn(...args: Parameters<typeof createWrapper>): Promise<VueWrapper<InstanceType<typeof AccountDetailsDrawer>>> {
  const wrapper = createWrapper(...args);
  await vi.advanceTimersByTimeAsync(DRAWER_SLIDE_MS);
  return wrapper;
}

const selectionActions = { 'selection-actions': '<div data-testid="selection-bar-stub" />' };

describe('modules/accounts/details/AccountDetailsDrawer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    set(groups, [address('0xmulti', ['eth', 'optimism', 'base']), address('0xsingle', ['eth'])]);
    set(accountId, undefined);
    set(view, undefined);
    set(settled, true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should push when opening with nothing showing and rewrite the entry when switching', async () => {
    const drawer = createWrapper().vm;

    await drawer.open('0xmulti');
    set(accountId, '0xmulti');
    await nextTick();
    await drawer.open('0xsingle');

    expect(open.mock.calls).toStrictEqual([['0xmulti', 'push'], ['0xsingle', 'replace']]);
  });

  it('should drop a key that names no account once the accounts have loaded, and not before', async () => {
    set(settled, false);
    set(accountId, '0xgone');
    createWrapper();
    await nextTick();

    expect(discard).not.toHaveBeenCalled();

    set(settled, true);
    await nextTick();

    expect(discard).toHaveBeenCalledOnce();
  });

  it('should stay closed while the URL names no account', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-details-drawer]').attributes('data-open')).toBe('false');
    expect(wrapper.find('[data-testid=account-details-content]').exists()).toBe(false);
  });

  it('should stay closed for an account the category does not hold', () => {
    set(accountId, '0xunknown');
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-details-drawer]').attributes('data-open')).toBe('false');
    expect(wrapper.find('[data-testid=account-details-content]').exists()).toBe(false);
  });

  it('should show the header at once and mount the lists only once the slide in is over', async () => {
    set(accountId, '0xmulti');
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-details-close]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=assets-stub]').exists()).toBe(false);

    await vi.advanceTimersByTimeAsync(DRAWER_SLIDE_MS);

    expect(wrapper.find('[data-testid=assets-stub]').exists()).toBe(true);
  });

  it('should keep the account on show while the drawer slides out, and drop it once the slide is over', async () => {
    set(accountId, '0xmulti');
    const wrapper = await createSlidIn();

    set(accountId, undefined);
    await nextTick();

    expect(wrapper.find('[data-testid=account-details-drawer]').attributes('data-open')).toBe('false');
    expect(wrapper.find('[data-testid=assets-stub]').attributes('data-chains')).toBe('eth,optimism,base');

    await wrapper.find('[data-testid=slid-out]').trigger('click');

    expect(wrapper.find('[data-testid=account-details-content]').exists()).toBe(false);
  });

  it('should stay on the tab it was on while it slides out, though the URL drops the tab with the account', async () => {
    set(accountId, '0xmulti');
    set(view, 'chains');
    const wrapper = await createSlidIn();

    set(accountId, undefined);
    set(view, undefined);
    await nextTick();

    expect(wrapper.findAll('[data-testid=chain-section-stub]')).toHaveLength(3);
    expect(wrapper.find('[data-testid=assets-stub]').exists()).toBe(false);
  });

  it('should open on the assets of the account, without the chains the row filtered out', async () => {
    set(accountId, '0xmulti');
    const wrapper = await createSlidIn({ '0xmulti': ['base'] });

    expect(wrapper.find('[data-testid=assets-stub]').attributes('data-chains')).toBe('eth,optimism');
    expect(wrapper.findAll('[data-testid^=account-details-tab-]').map(tab => tab.text())).toStrictEqual(['common.assets', 'account_balances.per_chain', 'account_balances.accounts']);
  });

  it('should show one section per chain the row keeps when the URL asks for the chains tab', async () => {
    set(accountId, '0xmulti');
    set(view, 'chains');
    const wrapper = await createSlidIn({ '0xmulti': ['optimism'] });

    expect(wrapper.findAll('[data-testid=chain-section-stub]').map(section => section.attributes('data-chain'))).toStrictEqual(['eth', 'base']);
    expect(wrapper.find('[data-testid=table-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=tabs]').attributes('data-index')).toBe('1');
  });

  it('should start the assets of another account afresh when it switches in place', async () => {
    set(accountId, '0xmulti');
    await createSlidIn();
    expect(assetsMounted).toHaveBeenCalledOnce();

    set(accountId, '0xsingle');
    await nextTick();

    expect(assetsMounted).toHaveBeenCalledTimes(2);
  });

  it('should list the account on each chain of a multi-chain address in the accounts tab, for editing one chain', async () => {
    set(accountId, '0xmulti');
    set(view, 'accounts');
    const wrapper = await createSlidIn({ '0xmulti': ['base'] });

    const table = wrapper.find('[data-testid=table-stub]');
    expect(table.attributes('data-group')).toBe('0xmulti');
    expect(table.attributes('data-chains')).toBe('eth,optimism');
    expect(wrapper.findAll('[data-testid^=account-details-tab-]').map(tab => tab.text())).toStrictEqual(['common.assets', 'account_balances.per_chain', 'account_balances.accounts']);
  });

  it('should list the derived addresses of an xpub in the addresses tab', async () => {
    set(groups, [createMock<BlockchainAccountGroupWithBalance>({ chains: ['btc'], derivationPath: undefined, expansion: 'accounts', kind: AccountKind.XPUB, xpub: 'xpub1' })]);
    set(accountId, 'xpub1#btc');
    set(view, 'addresses');
    const wrapper = await createSlidIn();

    expect(wrapper.find('[data-testid=table-stub]').attributes('data-group')).toBe('xpub1#btc');
  });

  it('should fall back to assets and show no tabs when the account has nothing else to list', async () => {
    set(accountId, '0xsingle');
    set(view, 'chains');
    const wrapper = await createSlidIn();

    expect(wrapper.find('[data-testid=assets-stub]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=tabs]').exists()).toBe(false);
  });

  it('should write the picked tab to the URL', async () => {
    set(accountId, '0xmulti');
    const wrapper = createWrapper();

    wrapper.findComponent({ name: 'RuiTabs' }).vm.$emit('update:modelValue', 1);
    await nextTick();

    expect(setView).toHaveBeenCalledWith('chains');
  });

  it('should show the selection actions it is handed above the list, inside the drawer, in selection mode', () => {
    set(accountId, '0xmulti');
    const wrapper = createWrapper({}, { selectionMode: true, slots: selectionActions });

    const bar = wrapper.find('[data-testid=account-details-selection-actions]');
    expect(bar.find('[data-testid=selection-bar-stub]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=account-details-drawer]').element.contains(bar.element)).toBe(true);
  });

  it('should drop the selection bar once selection mode ends', async () => {
    set(accountId, '0xmulti');
    const wrapper = createWrapper({}, { selectionMode: true, slots: selectionActions });

    await wrapper.setProps({ selectionMode: false });

    expect(wrapper.find('[data-testid=account-details-selection-actions]').exists()).toBe(false);
  });

  it('should leave no empty selection bar when it is handed no actions', () => {
    set(accountId, '0xmulti');

    expect(createWrapper({}, { selectionMode: true }).find('[data-testid=account-details-selection-actions]').exists()).toBe(false);
  });

  it('should close on Escape from anywhere inside the drawer', async () => {
    set(accountId, '0xmulti');
    const wrapper = await createSlidIn();

    await wrapper.find('[data-testid=assets-stub]').trigger('keydown', { key: 'Escape' });

    expect(close).toHaveBeenCalledOnce();
  });

  it('should put a search over the assets tab only', async () => {
    set(accountId, '0xmulti');

    expect((await createSlidIn()).find('[data-testid=assets-stub]').attributes('data-searchable')).toBe('true');
  });

  it('should close from the close button and from the scrim', async () => {
    set(accountId, '0xmulti');
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=account-details-close]').trigger('click');
    await wrapper.find('[data-testid=scrim]').trigger('click');

    expect(close).toHaveBeenCalledTimes(2);
  });
});
