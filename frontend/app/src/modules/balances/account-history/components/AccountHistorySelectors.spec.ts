import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { AccountHistoryRange } from '@/modules/balances/account-history/account-history-selection';
import AccountHistorySelectors from '@/modules/balances/account-history/components/AccountHistorySelectors.vue';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { createRuiPlugin } from '@/plugins/rui';

const { fetchLocationLabels } = vi.hoisted(() => ({ fetchLocationLabels: vi.fn<() => Promise<void>>() }));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: (): { fetchLocationLabels: typeof fetchLocationLabels } => ({ fetchLocationLabels }),
}));

const stubs = {
  AssetSelect: {
    name: 'AssetSelect',
    emits: ['update:modelValue'],
    props: ['modelValue', 'source', 'disabled', 'hint'],
    template: '<div data-testid="asset-stub" />',
  },
  LocationLabelSelector: {
    name: 'LocationLabelSelector',
    emits: ['update:modelValue'],
    props: ['modelValue', 'options'],
    template: '<div data-testid="account-stub" />',
  },
  LocationSelector: {
    name: 'LocationSelector',
    emits: ['update:modelValue'],
    props: ['modelValue', 'items', 'disabled'],
    template: '<div data-testid="location-stub" />',
  },
};

interface Models {
  restrictAssets?: boolean;
  account?: string;
  asset?: string;
  assets?: string[];
  location?: string;
  locations?: string[];
}

function createWrapper(models: Models = {}): VueWrapper<InstanceType<typeof AccountHistorySelectors>> {
  return mount(AccountHistorySelectors, {
    global: { plugins: [createRuiPlugin({})], stubs },
    props: {
      account: models.account,
      asset: models.asset,
      assets: models.assets ?? ['ETH', 'DAI'],
      location: models.location,
      locations: models.locations ?? ['ethereum'],
      range: AccountHistoryRange.ALL,
      restrictAssets: models.restrictAssets,
    },
  });
}

describe('account history selectors', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    fetchLocationLabels.mockReset().mockResolvedValue();
  });

  it('should load the accounts once when none are known yet', () => {
    createWrapper();
    expect(fetchLocationLabels).toHaveBeenCalledOnce();

    fetchLocationLabels.mockClear();
    useHistoryStore().setLocationLabels([{ location: 'ethereum', locationLabel: '0xA' }]);
    createWrapper();
    expect(fetchLocationLabels).not.toHaveBeenCalled();
  });

  it('should read a cleared account picker as no account', async () => {
    const wrapper = createWrapper({ account: '0xA' });

    wrapper.findComponent({ name: 'LocationLabelSelector' }).vm.$emit('update:modelValue', '');
    await nextTick();

    expect(wrapper.emitted('update:account')).toEqual([[undefined]]);
  });

  it('should offer only the assets the account has held, once an account is picked', () => {
    const noAccount = createWrapper().findComponent({ name: 'AssetSelect' });
    const withAccount = createWrapper({ account: '0xA' }).findComponent({ name: 'AssetSelect' });

    expect(noAccount.props('disabled')).toBe(true);
    expect(withAccount.props('disabled')).toBe(false);
    expect(withAccount.props('source')).toMatchObject({ items: ['ETH', 'DAI'] });
  });

  it('should hand the linked asset to the picker only once the asset list is in, so the picker cannot drop it on load', async () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH', assets: [] });
    const assetSelect = wrapper.findComponent({ name: 'AssetSelect' });
    expect(assetSelect.props('modelValue')).toBeUndefined();

    await wrapper.setProps({ assets: ['ETH', 'DAI'] });

    expect(assetSelect.props('modelValue')).toBe('ETH');
  });

  it('should ignore the empty value the picker writes back while the asset is held back', async () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH', assets: [] });

    wrapper.findComponent({ name: 'AssetSelect' }).vm.$emit('update:modelValue', '');
    await nextTick();

    expect(wrapper.emitted('update:asset')).toBeUndefined();
  });

  it('should read an emptied asset picker as a cleared asset once the list is in', async () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH' });

    wrapper.findComponent({ name: 'AssetSelect' }).vm.$emit('update:modelValue', '');
    await nextTick();

    expect(wrapper.emitted('update:asset')).toEqual([[undefined]]);
  });

  it('should warn in the asset hint that assets may be missing while events are unprocessed', async () => {
    const wrapper = createWrapper({ account: '0xA' });
    const assetSelect = wrapper.findComponent({ name: 'AssetSelect' });
    expect(assetSelect.props('hint')).toBe('account_history.selectors.asset_hint');

    await wrapper.setProps({ assetsProcessingRequired: true });

    expect(assetSelect.props('hint')).toBe('account_history.selectors.asset_hint_processing');
  });

  it('should only let the location be narrowed when the asset is held in more than one', () => {
    const one = createWrapper({ locations: ['ethereum'] }).findComponent({ name: 'LocationSelector' });
    const two = createWrapper({ locations: ['ethereum', 'optimism'] }).findComponent({ name: 'LocationSelector' });

    expect(one.props('disabled')).toBe(true);
    expect(two.props('disabled')).toBe(false);
  });

  it('should emit the picked range', async () => {
    const wrapper = createWrapper({ account: '0xA' });

    await wrapper.find(`[data-testid=account-history-range-${AccountHistoryRange.MONTH}]`).trigger('click');

    expect(wrapper.emitted('update:range')).toEqual([[AccountHistoryRange.MONTH]]);
  });

  it('should offer any asset, at once and without the held-assets hint, when the list is not restricted', () => {
    const assetSelect = createWrapper({ account: '0xA', asset: 'ETH', assets: [], restrictAssets: false })
      .findComponent({ name: 'AssetSelect' });

    expect(assetSelect.props('modelValue')).toBe('ETH');
    expect(assetSelect.props('source')).not.toHaveProperty('items');
    expect(assetSelect.props('hint')).toBeUndefined();
  });
});
