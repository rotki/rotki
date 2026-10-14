import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import EvmAccountsRefreshMenu from '@/modules/accounts/EvmAccountsRefreshMenu.vue';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';

const isDetectingTokens = ref<boolean>(false);
const refreshDisabled = ref<boolean>(false);
const massDetectTokens = vi.fn(async (): Promise<void> => {});

vi.mock('@/modules/accounts/use-blockchain-account-loading', () => ({
  useBlockchainAccountLoading: vi.fn(() => ({
    isDetectingTokens: computed<boolean>(() => get(isDetectingTokens)),
    refreshDisabled: computed<boolean>(() => get(refreshDisabled)),
  })),
}));

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: vi.fn(() => ({ massDetectTokens })),
}));

const stubs = {
  BlockchainBalanceRefreshBehaviourMenu: { template: '<div data-testid="behaviour-menu" />' },
  DetectEvmAccounts: { template: '<div data-testid="detect-evm-accounts" />' },
  DetectTokenChainsSelection: {
    emits: ['redetect:all', 'done'],
    template: '<div data-testid="chains-selection"><button data-testid="chains-all" @click="$emit(\'redetect:all\')" /><button data-testid="chains-done" @click="$emit(\'done\')" /></div>',
  },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled"><slot /></button>',
  },
  RuiDivider: true,
  RuiIcon: true,
};

function createWrapper(): VueWrapper<InstanceType<typeof EvmAccountsRefreshMenu>> {
  return mount(EvmAccountsRefreshMenu, { global: { stubs } });
}

describe('modules/accounts/EvmAccountsRefreshMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(isDetectingTokens, false);
    set(refreshDisabled, false);
  });

  it('should read the loading state of the EVM accounts', () => {
    createWrapper();

    expect(useBlockchainAccountLoading).toHaveBeenCalledWith('evm');
  });

  it('should ask in place before a full re-detect, and run it only once confirmed', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-menu-redetect-all]').trigger('click');

    expect(wrapper.find('[data-testid=refresh-menu-redetect-confirm]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=refresh-menu-redetect-all]').exists()).toBe(false);
    expect(massDetectTokens).not.toHaveBeenCalled();

    await wrapper.find('[data-testid=refresh-menu-redetect-confirm-run]').trigger('click');

    expect(massDetectTokens).toHaveBeenCalledOnce();
    expect(wrapper.emitted('close')).toEqual([[]]);
    expect(wrapper.find('[data-testid=refresh-menu-redetect-confirm]').exists()).toBe(false);
  });

  it('should go back to the entries when the re-detect is cancelled', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-menu-redetect-all]').trigger('click');
    await wrapper.find('[data-testid=refresh-menu-redetect-confirm] button').trigger('click');

    expect(wrapper.find('[data-testid=refresh-menu-redetect-confirm]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=refresh-menu-redetect-all]').exists()).toBe(true);
    expect(massDetectTokens).not.toHaveBeenCalled();
    expect(wrapper.emitted('close')).toBeUndefined();
  });

  it('should open the chain picker and come back from it', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-menu-redetect-chains]').trigger('click');

    expect(wrapper.find('[data-testid=chains-selection]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=refresh-menu-redetect-all]').exists()).toBe(false);

    await wrapper.find('[data-testid=refresh-menu-back]').trigger('click');

    expect(wrapper.find('[data-testid=chains-selection]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=refresh-menu-redetect-all]').exists()).toBe(true);
  });

  it('should ask for the full re-detect when every chain is picked', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-menu-redetect-chains]').trigger('click');
    await wrapper.find('[data-testid=chains-all]').trigger('click');

    expect(wrapper.find('[data-testid=chains-selection]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=refresh-menu-redetect-confirm]').exists()).toBe(true);
  });

  it('should close once the picked chains start detecting', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-menu-redetect-chains]').trigger('click');
    await wrapper.find('[data-testid=chains-done]').trigger('click');

    expect(wrapper.emitted('close')).toEqual([[]]);
  });

  it.each([
    ['a refresh cannot start', refreshDisabled],
    ['tokens are being detected', isDetectingTokens],
  ])('should disable both re-detect entries while %s', async (_, state) => {
    const wrapper = createWrapper();
    set(state, true);
    await nextTick();

    expect(wrapper.find('[data-testid=refresh-menu-redetect-all]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=refresh-menu-redetect-chains]').attributes('disabled')).toBeDefined();
  });

  it('should keep account detection and the refresh behaviour settings in the menu', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=detect-evm-accounts]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=behaviour-menu]').exists()).toBe(true);
  });
});
