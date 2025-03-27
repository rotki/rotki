import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { HistoryEventEntryType, One } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    fetchHistoricPrices: vi.fn(),
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

describe('component/HistoryEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventForm>>;

  const createWrapper = () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(HistoryEventForm, {
      props: {
        data: { nextSequenceId: '0' },
      },
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
    setupDayjs();
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
    vi.useFakeTimers();
  });

  beforeEach(async () => {
    wrapper = createWrapper();
    await nextTick();
    await flushPromises();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  afterAll(() => {
    vi.useRealTimers();
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
    await vi.advanceTimersToNextTimerAsync();

    const options = wrapper.find('[role="menu-content"]').findAll('button');
    for (const option of options) {
      if (option.text() === value) {
        await option.trigger('click');
        await vi.advanceTimersToNextTimerAsync();
        break;
      }
    }

    const id = value.split(/ /g).join('-');
    expect(wrapper.find(`[data-cy=${id}-form]`).exists()).toBeTruthy();
  });
});
