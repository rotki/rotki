import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import HistoricPriceFormDialog from '@/modules/assets/prices/historic/HistoricPriceFormDialog.vue';
import '@test/i18n';

const { save } = vi.hoisted(() => ({ save: vi.fn() }));

vi.mock('@/modules/assets/prices/use-historic-price-manager', () => ({
  useHistoricPrices: (): Record<string, unknown> => ({ save }),
}));

/** Stands in for the form, passing validation so a confirm reaches the save. */
const HistoricPriceForm = defineComponent({
  name: 'HistoricPriceForm',
  props: ['modelValue'],
  setup(_props, { expose }) {
    expose({ validate: (): boolean => true });
    return {};
  },
  template: '<div />',
});

const payload: HistoricalPriceFormPayload = { fromAsset: 'ETH', price: '1600', sourceType: 'manual', timestamp: 1_700_000_000, toAsset: 'USD' };

function createWrapper(editMode = false): VueWrapper {
  return mount(HistoricPriceFormDialog, {
    global: {
      stubs: {
        BigDialog: { props: ['display'], emits: ['confirm'], template: '<div v-if="display"><slot /><button data-testid="confirm" @click="$emit(\'confirm\')" /></div>' },
        HistoricPriceForm,
      },
    },
    props: { editMode, modelValue: { ...payload } },
  });
}

describe('historicPriceFormDialog', () => {
  beforeEach(() => {
    save.mockReset();
  });

  it('should name a failed save and keep the form open with what was typed', async () => {
    save.mockResolvedValue(err(new Error('rejected')));
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=confirm]').trigger('click');
    await nextTick();

    const strip = wrapper.find('[data-testid=historic-price-save-error]');
    expect(strip.text()).toContain('price_management.add.error.title');
    expect(strip.text()).toContain('rejected');
    expect(wrapper.findComponent(HistoricPriceForm).props('modelValue')).toMatchObject(payload);
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should name an edit as an edit when its save fails', async () => {
    save.mockResolvedValue(err(new Error('rejected')));
    const wrapper = createWrapper(true);

    await wrapper.find('[data-testid=confirm]').trigger('click');
    await nextTick();

    expect(wrapper.find('[data-testid=historic-price-save-error]').text()).toContain('price_management.edit.error.title');
  });

  it('should close and ask for a refresh once the save succeeds', async () => {
    save.mockResolvedValue(ok(true));
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=confirm]').trigger('click');
    await nextTick();

    expect(wrapper.emitted('refresh')).toHaveLength(1);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });
});
