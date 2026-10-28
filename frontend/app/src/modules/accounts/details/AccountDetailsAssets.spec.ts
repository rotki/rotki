import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AccountDetailsAssets from '@/modules/accounts/details/AccountDetailsAssets.vue';

const { assets } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { assets: ref<AssetBalanceWithPrice[]>([]) };
});

vi.mock('@/modules/balances/use-aggregated-balances', async () => {
  const { computed } = await import('vue');
  return {
    useAggregatedBalances: (): object => ({
      useBlockchainBalances: (_chains: unknown, _group: unknown, kind?: string): unknown =>
        computed<AssetBalanceWithPrice[]>(() => (kind === 'liabilities' ? [] : get(assets))),
    }),
  };
});

const stubs = {
  AccountAssetBalances: true,
  AssetBalances: { name: 'AssetBalances', props: ['search', 'balances'], template: '<div data-testid="asset-balances-stub" />' },
  TableSearchField: {
    emits: ['update:modelValue'],
    props: ['modelValue'],
    template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
};

function asset(id: string, value: number): AssetBalanceWithPrice {
  return createMock<AssetBalanceWithPrice>({ asset: id, value: bigNumberify(value) });
}

function createWrapper(props: { searchable?: boolean; limit?: number } = {}): VueWrapper {
  return mount(AccountDetailsAssets, {
    global: { stubs },
    props: { chains: ['eth'], groupId: '0x1', selected: undefined, ...props },
    slots: { header: '<template #header="{ value }"><span data-testid="header-value">{{ value.toString() }}</span></template>' },
  });
}

function listed(wrapper: VueWrapper): string[] {
  return wrapper.findComponent({ name: 'AssetBalances' }).props('balances').map((item: AssetBalanceWithPrice) => item.asset);
}

describe('modules/accounts/details/AccountDetailsAssets', () => {
  beforeEach(() => {
    set(assets, [asset('A', 1), asset('B', 30), asset('C', 5), asset('D', 20)]);
  });

  it('should hand its header the value of every asset in scope, the ones past the limit too', () => {
    expect(createWrapper({ limit: 2 }).find('[data-testid=header-value]').text()).toBe('56');
  });

  it('should narrow the assets to what is typed in its search', async () => {
    const wrapper = createWrapper({ searchable: true });

    await wrapper.find('[data-testid=account-details-assets-search]').setValue('arb');

    expect(wrapper.findComponent({ name: 'AssetBalances' }).props('search')).toBe('arb');
  });

  it('should show no search unless asked for one', () => {
    expect(createWrapper().find('[data-testid=account-details-assets-search]').exists()).toBe(false);
  });

  it('should list only the most valuable assets up to the limit', () => {
    expect(listed(createWrapper({ limit: 2 }))).toEqual(['B', 'D']);
  });

  it('should list every asset once show all is clicked, and go back to the top ones on a second click', async () => {
    const wrapper = createWrapper({ limit: 2 });
    const button = wrapper.find('[data-testid=account-details-assets-show-all]');

    expect(button.text()).toBe('account_balances.show_all_assets::4');

    await button.trigger('click');

    expect(listed(wrapper)).toEqual(['A', 'B', 'C', 'D']);
    expect(button.text()).toBe('account_balances.show_top_assets::2');

    await button.trigger('click');

    expect(listed(wrapper)).toEqual(['B', 'D']);
  });

  it('should list everything with no show all when the assets fit the limit', () => {
    const wrapper = createWrapper({ limit: 4 });

    expect(listed(wrapper)).toEqual(['A', 'B', 'C', 'D']);
    expect(wrapper.find('[data-testid=account-details-assets-show-all]').exists()).toBe(false);
  });

  it('should list everything when there is no limit', () => {
    const wrapper = createWrapper();

    expect(listed(wrapper)).toEqual(['A', 'B', 'C', 'D']);
    expect(wrapper.find('[data-testid=account-details-assets-show-all]').exists()).toBe(false);
  });
});
