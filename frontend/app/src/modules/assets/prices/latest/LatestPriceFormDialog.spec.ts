import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import '@test/i18n';

const { save } = vi.hoisted(() => ({ save: vi.fn() }));

vi.mock('@/modules/assets/prices/use-latest-price-manager', () => ({
  useLatestPrices: (): Record<string, unknown> => ({ save }),
}));

/** Stands in for the form, passing validation so a confirm reaches the save. */
const LatestPriceForm = defineComponent({
  name: 'LatestPriceForm',
  props: ['modelValue'],
  setup(_props, { expose }) {
    expose({ validate: (): boolean => true });
    return {};
  },
  template: '<div />',
});

const item: ManualPriceFormPayload = { fromAsset: 'ETH', price: '5', toAsset: 'USD' };

function createWrapper(props: Record<string, unknown>): VueWrapper {
  return mount(LatestPriceFormDialog, {
    global: {
      stubs: {
        BigDialog: { props: ['title', 'display'], emits: ['confirm'], template: '<div v-if="display" data-testid="dlg" :data-title="title"><slot /><button data-testid="confirm" @click="$emit(\'confirm\')" /></div>' },
        LatestPriceForm,
      },
    },
    props: { open: true, ...props },
  });
}

describe('latestPriceFormDialog', () => {
  beforeEach(() => {
    save.mockReset();
  });

  it('should name a failed save and keep the form open with what was typed', async () => {
    save.mockResolvedValue(err(new Error('the pair already has a price')));
    const wrapper = createWrapper({ editableItem: null, prefill: item });
    await nextTick();

    await wrapper.find('[data-testid=confirm]').trigger('click');
    await nextTick();

    const strip = wrapper.find('[data-testid=latest-price-save-error]');
    expect(strip.text()).toContain('price_management.add.error.title');
    expect(strip.text()).toContain('the pair already has a price');
    expect(wrapper.findComponent(LatestPriceForm).props('modelValue')).toMatchObject(item);
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should close and ask for a refresh once the save succeeds', async () => {
    save.mockResolvedValue(ok(true));
    const wrapper = createWrapper({ editableItem: item });
    await nextTick();

    await wrapper.find('[data-testid=confirm]').trigger('click');
    await nextTick();

    expect(wrapper.emitted('refresh')).toHaveLength(1);
    expect(wrapper.find('[data-testid=latest-price-save-error]').exists()).toBe(false);
  });

  it('should show the edit title when an editable item is provided', async () => {
    const wrapper = createWrapper({ editableItem: item });
    await nextTick();
    expect(wrapper.find('[data-testid=dlg]').attributes('data-title')).toContain('edit_title');
  });

  it('should show the add title when there is no editable item', async () => {
    const wrapper = createWrapper({ editableItem: null });
    await nextTick();
    expect(wrapper.find('[data-testid=dlg]').attributes('data-title')).toContain('add_title');
  });

  it('should keep the add title but seed the form when prefilled', async () => {
    const prefill: ManualPriceFormPayload = { fromAsset: 'ETH', price: '', toAsset: 'USD' };
    const wrapper = createWrapper({ prefill });
    await nextTick();

    expect(wrapper.find('[data-testid=dlg]').attributes('data-title')).toContain('add_title');
    expect(wrapper.findComponent({ name: 'LatestPriceForm' }).props('modelValue')).toMatchObject(prefill);
  });
});
