import type { LocationQuery, RouteLocationNormalizedLoaded } from 'vue-router';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef, ref, type Ref } from 'vue';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';
import EvmAccountsPage from '@/pages/accounts/evm/[[tab]].vue';

const routeQuery = ref<LocationQuery>({});
const replaceMock = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: (): ComputedRef<Pick<RouteLocationNormalizedLoaded, 'params' | 'query'>> =>
    computed(() => ({ params: { tab: 'accounts' }, query: routeQuery.value })),
  useRouter: (): { replace: typeof replaceMock; push: ReturnType<typeof vi.fn> } => ({
    replace: replaceMock,
    push: vi.fn(),
  }),
}));

vi.mock('@/modules/accounts/use-account-category-helper', () => ({
  useAccountCategoryHelper: (): { chainIds: ComputedRef<string[]> } => ({
    chainIds: computed<string[]>(() => ['eth', 'optimism']),
  }),
}));

vi.mock('@/modules/accounts/use-account-import-progress-store', () => ({
  useAccountImportProgressStore: (): { importingAccounts: Ref<boolean> } => ({
    importingAccounts: ref(false),
  }),
}));

vi.mock('@/modules/session/use-module-enabled', async () => {
  const actual = await vi.importActual<typeof import('@/modules/session/use-module-enabled')>(
    '@/modules/session/use-module-enabled',
  );
  return {
    ...actual,
    useModuleEnabled: (): { enabled: Ref<boolean> } => ({ enabled: ref(false) }),
  };
});

vi.mock('@/modules/staking/eth/use-eth-staking-access', () => ({
  useEthStakingAccess: (): { allowed: Ref<boolean> } => ({ allowed: ref(true) }),
}));

function mountPage(): VueWrapper<InstanceType<typeof EvmAccountsPage>> {
  return mount(EvmAccountsPage, {
    props: { tab: 'accounts' },
    global: {
      provide: libraryDefaults,
      stubs: {
        AccountBalances: { template: '<div />' },
        EthStakingValidators: { template: '<div />' },
        EvmAccountPageButtons: { template: '<div />' },
        AccountImportProgress: { template: '<div />' },
        BlockchainBalanceStalenessIndicator: { template: '<div />' },
        TablePageLayout: { template: '<div><slot name="buttons" /><slot name="tabs" /><slot /></div>' },
        AccountDialog: {
          props: ['modelValue', 'chainIds', 'showAllChainsOption'],
          emits: ['update:modelValue', 'complete'],
          template: '<div data-cy="account-dialog-stub" />',
        },
        RuiTabs: true,
        RuiTab: true,
        Transition: { template: '<div><slot /></div>' },
      },
    },
  });
}

function isAccountManageState(value: unknown): value is AccountManageState {
  return typeof value === 'object' && value !== null && 'mode' in value && 'data' in value;
}

function getDialogModel(wrapper: VueWrapper<InstanceType<typeof EvmAccountsPage>>): AccountManageState | undefined {
  const value: unknown = wrapper.findComponent(AccountDialog).props('modelValue');
  return isAccountManageState(value) ? value : undefined;
}

function getFirstAddress(model: AccountManageState | undefined): string | undefined {
  if (!model || !Array.isArray(model.data))
    return undefined;
  const first = model.data[0];
  return first && 'address' in first ? first.address : undefined;
}

describe('pages/accounts/evm — add query handling', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmAccountsPage>>;

  beforeEach(() => {
    setActivePinia(createPinia());
    routeQuery.value = {};
    replaceMock.mockReset();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should open the account dialog when navigated with ?add=true', async () => {
    routeQuery.value = { add: 'true' };
    wrapper = mountPage();
    await flushPromises();

    const model = getDialogModel(wrapper);

    expect(model).toBeDefined();
    expect(model?.mode).toBe('add');
    expect(model?.type).toBe('account');
    expect(getFirstAddress(model)).toBe('');
    expect(replaceMock).toHaveBeenCalledWith({ query: {} });
  });

  it('should prefill the address when ?add=true&addressToAdd=0x... is present', async () => {
    const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
    routeQuery.value = { add: 'true', addressToAdd: address };
    wrapper = mountPage();
    await flushPromises();

    const model = getDialogModel(wrapper);

    expect(model).toBeDefined();
    expect(getFirstAddress(model)).toBe(address);
    expect(replaceMock).toHaveBeenCalledWith({ query: {} });
  });

  it('should not open the dialog without ?add', async () => {
    wrapper = mountPage();
    await flushPromises();

    expect(getDialogModel(wrapper)).toBeUndefined();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
