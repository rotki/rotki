import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import '@test/i18n';

vi.mock('@/modules/assets/prices/use-latest-price-manager', () => ({
  useLatestPrices: (): Record<string, unknown> => ({ save: vi.fn() }),
}));

const item: ManualPriceFormPayload = { fromAsset: 'ETH', price: '5', toAsset: 'USD' };

function createWrapper(props: Record<string, unknown>): VueWrapper {
  return mount(LatestPriceFormDialog, {
    global: {
      stubs: {
        BigDialog: { props: ['title', 'display'], template: '<div v-if="display" data-testid="dlg" :data-title="title"><slot /></div>' },
        LatestPriceForm: { name: 'LatestPriceForm', props: ['modelValue'], template: '<div />' },
      },
    },
    props: { open: true, ...props },
  });
}

describe('latestPriceFormDialog', () => {
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
