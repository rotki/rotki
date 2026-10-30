import { HistoryEventEntryType } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { kebabCase } from 'es-toolkit';
import { createPinia, setActivePinia } from 'pinia';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { setupDayjs } from '@/modules/core/common/data/date';
import HistoryEventForm from '@/modules/history/events/HistoryEventForm.vue';

type Wrapper = VueWrapper<InstanceType<typeof HistoryEventForm>>;

async function createWrapper(entryType: HistoryEventEntryType): Promise<Wrapper> {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(HistoryEventForm, {
    global: {
      plugins: [pinia],
      stubs: {
        RuiAutoComplete: false,
        Teleport: true,
        TransitionGroup: false,
      },
    },
    props: {
      data: { nextSequenceId: '0', type: 'add' },
      entryType,
    },
  });
  await vi.advanceTimersToNextTimerAsync();
  return wrapper;
}

describe('component/HistoryEventForm.vue', () => {
  beforeAll(() => {
    setupDayjs();
    vi.useFakeTimers();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  it.each(Object.values(HistoryEventEntryType))('should render the %s form for its entry type', async (entryType) => {
    const wrapper = await createWrapper(entryType);

    expect(wrapper.find(`[data-testid=event-form][data-key="${kebabCase(entryType)}"]`).exists()).toBe(true);
  });

  it('should switch forms when the entry type picked above it changes', async () => {
    const wrapper = await createWrapper(HistoryEventEntryType.HISTORY_EVENT);

    await wrapper.setProps({ entryType: HistoryEventEntryType.SWAP_EVENT });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=event-form][data-key=swap-event]').exists()).toBe(true);
  });
});
