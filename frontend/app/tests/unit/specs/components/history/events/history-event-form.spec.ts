import { type VueWrapper, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { HistoryEventEntryType } from '@rotki/common';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import flushPromises from 'flush-promises';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    fetchHistoricPrices: vi.fn(),
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

describe('historyEventForm.vue', () => {
  setupDayjs();
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventForm>>;

  const createWrapper = () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(HistoryEventForm, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiAutoComplete: false,
          Teleport: true,
          TransitionGroup: false,
        },
      },
    });
  };

  beforeAll(() => {
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  beforeEach(async () => {
    wrapper = createWrapper();
    await nextTick();
    await flushPromises();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should default to history event form', () => {
    expect.assertions(2);

    const entryTypeInput = wrapper.find('[data-cy="entry-type"] input');
    const entryTypeElement = entryTypeInput.element as HTMLInputElement;

    expect(entryTypeElement.value).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(wrapper.find('[data-cy=history-event-form]').exists()).toBeTruthy();
  });

  it.each(Object.values(HistoryEventEntryType))('changes to proper form %s', async (value: string) => {
    await wrapper.find('[data-cy="entry-type"] [data-id="activator"]').trigger('click');
    await nextTick();
    await flushPromises();

    const options = wrapper.find('[role="menu-content"]').findAll('button');
    for (const option of options) {
      if (option.text() === value) {
        await option.trigger('click');
        await nextTick();
        await flushPromises();
        break;
      }
    }

    const id = value.split(/ /g).join('-');
    expect(wrapper.find(`[data-cy=${id}-form]`).exists()).toBeTruthy();
  });
});
