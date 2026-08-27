import type { KrakenStakingDateFilter } from '@/modules/staking/staking-types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import KrakenDateFilter from '@/modules/staking/kraken/KrakenDateFilter.vue';

function createWrapper(modelValue: KrakenStakingDateFilter): VueWrapper {
  return shallowMount(KrakenDateFilter, {
    global: { plugins: [createCustomPinia()] },
    props: { modelValue },
  });
}

function barOf(wrapper: VueWrapper): ReturnType<typeof shallowMount<typeof PillFilterBar>> {
  return wrapper.findComponent(PillFilterBar);
}

describe('krakenDateFilter', () => {
  it('should offer a single period field', () => {
    const wrapper = createWrapper({});
    const fields = barOf(wrapper).props('fields');
    expect(fields).toHaveLength(1);
    expect(fields[0]).toMatchObject({
      bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
      key: 'period',
      valueType: 'date',
    });
  });

  it('should pass the model bounds to the bar as strings', () => {
    const wrapper = createWrapper({ fromTimestamp: 1600000000, toTimestamp: 1700000000 });
    expect(barOf(wrapper).props('matches')).toEqual({
      fromTimestamp: '1600000000',
      toTimestamp: '1700000000',
    });
  });

  it('should send no bound the model does not hold', () => {
    const wrapper = createWrapper({ fromTimestamp: 1600000000 });
    expect(barOf(wrapper).props('matches')).toEqual({ fromTimestamp: '1600000000' });
  });

  it('should write the bounds the bar reports back as numbers', async () => {
    const wrapper = createWrapper({});
    await barOf(wrapper).vm.$emit('update:matches', { fromTimestamp: '1600000000', toTimestamp: '1700000000' });
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{
      fromTimestamp: 1600000000,
      toTimestamp: 1700000000,
    }]);
  });

  it('should clear a bound the bar dropped', async () => {
    const wrapper = createWrapper({ fromTimestamp: 1600000000, toTimestamp: 1700000000 });
    await barOf(wrapper).vm.$emit('update:matches', { fromTimestamp: '1600000000' });
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{
      fromTimestamp: 1600000000,
      toTimestamp: undefined,
    }]);
  });
});
