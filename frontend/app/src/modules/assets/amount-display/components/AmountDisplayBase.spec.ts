import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import AmountDisplayBase from '@/modules/assets/amount-display/components/AmountDisplayBase.vue';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';

describe('modules/amount-display/components/AmountDisplayBase', () => {
  let wrapper: VueWrapper<InstanceType<typeof AmountDisplayBase>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    updateGeneralSettings({ uiFloatingPrecision: 2 });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  function copiedValue(value: string): string {
    wrapper = mount(AmountDisplayBase, {
      global: { plugins: [pinia] },
      props: { value: bigNumberify(value) },
    });
    return wrapper.findComponent(CopyTooltip).props('value');
  }

  it.each([
    ['0.000000001', '0.000000001'],
    ['-0.000000002', '-0.000000002'],
    ['1e-18', '0.000000000000000001'],
    ['1e21', '1000000000000000000000'],
    ['1234.5678', '1234.5678'],
  ])('should copy %s as the plain decimal %s', (value, expected) => {
    expect(copiedValue(value)).toBe(expected);
  });

  it('should copy a dash for NaN', () => {
    expect(copiedValue('NaN')).toBe('-');
  });
});
