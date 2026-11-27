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
      restrictAssets: props.restrictAssets,
    },
  });
}

function assetField(wrapper: VueWrapper<InstanceType<typeof AccountHistorySelectors>>): FieldDef | undefined {
  const fields: FieldDef[] = wrapper.findComponent({ name: 'PillFilterBar' }).props('fields');
  return fields.find(({ key }) => key === 'asset');
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

    wrapper.findComponent({ name: 'PillFilterBar' }).vm.$emit('update:params', { account: '0xB' });
    await nextTick();

    expect(wrapper.emitted('update:account')).toEqual([['0xB']]);
    expect(wrapper.emitted('update:asset')).toEqual([[undefined]]);
  });

  it('should offer the held assets with the list, and search every asset without it', () => {
    expect(assetField(createWrapper())?.suggest?.()).toEqual(['ETH', 'DAI']);
    expect(assetField(createWrapper({ restrictAssets: false }))?.searchAsset).toBeDefined();
  });

  it('should say assets may be missing while events are unprocessed, only for the held list', () => {
    expect(createWrapper({ assetsProcessingRequired: true }).find('[data-testid=account-history-assets-processing]').exists()).toBe(true);
    expect(createWrapper({ assetsProcessingRequired: false }).find('[data-testid=account-history-assets-processing]').exists()).toBe(false);
    expect(createWrapper({ assetsProcessingRequired: true, restrictAssets: false }).find('[data-testid=account-history-assets-processing]').exists()).toBe(false);
  });
});
