import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import AccountHistorySelectors from '@/modules/balances/account-history/components/AccountHistorySelectors.vue';
import { createRuiPlugin } from '@/plugins/rui';

interface Props {
  account?: string;
  asset?: string;
  assets?: string[];
  restrictAssets?: boolean;
  assetsProcessingRequired?: boolean;
  location?: string;
  locations?: string[];
}

function createWrapper(props: Props = {}): VueWrapper<InstanceType<typeof AccountHistorySelectors>> {
  return mount(AccountHistorySelectors, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        PillFilterBar: { name: 'PillFilterBar', emits: ['update:params'], props: ['params', 'fields', 'labels'], template: '<div />' },
      },
    },
    props: {
      account: props.account,
      asset: props.asset,
      assets: props.assets ?? ['ETH', 'DAI'],
      assetsProcessingRequired: props.assetsProcessingRequired,
      location: props.location,
      locations: props.locations ?? ['ethereum', 'optimism'],
      restrictAssets: props.restrictAssets,
    },
  });
}

function fieldOf(wrapper: VueWrapper<InstanceType<typeof AccountHistorySelectors>>, key: string): FieldDef | undefined {
  const fields: FieldDef[] = wrapper.findComponent({ name: 'PillFilterBar' }).props('fields');
  return fields.find(field => field.key === key);
}

describe('account history selectors', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show the picked account and asset as pills', () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH' });

    expect(wrapper.findComponent({ name: 'PillFilterBar' }).props('params')).toEqual({ account: '0xA', asset: 'ETH' });
  });

  it('should write a pill change back as the account and asset', async () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH' });

    wrapper.findComponent({ name: 'PillFilterBar' }).vm.$emit('update:params', { account: '0xB', location: 'optimism' });
    await nextTick();

    expect(wrapper.emitted('update:account')).toEqual([['0xB']]);
    expect(wrapper.emitted('update:asset')).toEqual([[undefined]]);
    expect(wrapper.emitted('update:location')).toEqual([['optimism']]);
  });

  it('should offer the held assets with the list, and search every asset without it', () => {
    expect(fieldOf(createWrapper(), 'asset')?.suggest?.()).toEqual(['ETH', 'DAI']);
    expect(fieldOf(createWrapper({ restrictAssets: false }), 'asset')?.searchAsset).toBeDefined();
  });

  it('should say assets may be missing while events are unprocessed, only for the held list', () => {
    expect(createWrapper({ assetsProcessingRequired: true }).find('[data-testid=account-history-assets-processing]').exists()).toBe(true);
    expect(createWrapper({ assetsProcessingRequired: false }).find('[data-testid=account-history-assets-processing]').exists()).toBe(false);
    expect(createWrapper({ assetsProcessingRequired: true, restrictAssets: false }).find('[data-testid=account-history-assets-processing]').exists()).toBe(false);
  });

  it('should offer a location pill with the held locations, and none without the held list', () => {
    expect(fieldOf(createWrapper(), 'location')?.suggest?.()).toEqual(['ethereum', 'optimism']);
    expect(fieldOf(createWrapper({ restrictAssets: false }), 'location')).toBeUndefined();
  });
});
