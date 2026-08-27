import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetBalanceStatisticSourceSetting from './AssetBalanceStatisticSourceSetting.vue';

vi.mock('@/modules/settings/use-asset-statistic-state', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    useAssetStatisticState: (): object => ({
      getPreference: (): undefined => undefined,
      modelUseHistoricalAssetBalances: shallowRef<boolean>(false),
      name: computed<string>(() => 'Ether'),
      rememberStateForAsset: shallowRef<boolean>(false),
      suppressIfPerAsset: async (func: () => Promise<void>): Promise<void> => func(),
    }),
  };
});

vi.mock('@/modules/settings/use-setting-model', async () => {
  const { shallowRef } = await import('vue');
  return {
    useSettingModel: (): object => ({ model: shallowRef<boolean>(false) }),
  };
});

const stubs = {
  MenuTooltipButton: true,
  RuiCardHeader: { template: '<div><slot name="header" /></div>' },
  RuiCheckbox: true,
  RuiIcon: true,
  RuiMenu: { template: '<div><slot /></div>' },
  RuiRadio: {
    props: ['value', 'label'],
    template: '<div data-testid="radio" :data-value="String(value)" :data-value-type="typeof value">{{ label }}</div>',
  },
  RuiRadioGroup: { template: '<div><slot /></div>' },
};

function createWrapper(): VueWrapper {
  return mount(AssetBalanceStatisticSourceSetting, { global: { stubs } });
}

describe('assetBalanceStatisticSourceSetting', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should bind each radio a boolean value, not the empty string a shorthand would pass', () => {
    const wrapper = createWrapper();
    const radios = wrapper.findAll('[data-testid=radio]');

    expect(radios).toHaveLength(2);
    expect(radios[0].attributes('data-value-type')).toBe('boolean');
    expect(radios[0].attributes('data-value')).toBe('false');
    expect(radios[1].attributes('data-value-type')).toBe('boolean');
    expect(radios[1].attributes('data-value')).toBe('true');
  });
});
