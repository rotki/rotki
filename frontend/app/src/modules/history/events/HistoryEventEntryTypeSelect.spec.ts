import type { EvmHistoryEvent } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import HistoryEventEntryTypeSelect from '@/modules/history/events/HistoryEventEntryTypeSelect.vue';

type Wrapper = VueWrapper<InstanceType<typeof HistoryEventEntryTypeSelect>>;

function createWrapper(data: GroupEventData | StandaloneEventData, modelValue: HistoryEventEntryType): Wrapper {
  return mount(HistoryEventEntryTypeSelect, {
    global: { stubs: { Teleport: true, TransitionGroup: false } },
    props: { data, modelValue },
  });
}

async function openOptions(wrapper: Wrapper): Promise<string[]> {
  await wrapper.find('[data-testid=entry-type] [data-id=activator]').trigger('click');
  await vi.advanceTimersToNextTimerAsync();
  return wrapper.find('[data-id="content"]').findAll('button').map(option => option.text());
}

describe('historyEventEntryTypeSelect', () => {
  beforeAll(() => {
    vi.useFakeTimers();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  it('should show the entry type it is given', () => {
    const wrapper = createWrapper({ nextSequenceId: '0', type: 'add' }, HistoryEventEntryType.SWAP_EVENT);

    expect(wrapper.find<HTMLInputElement>('[data-testid=entry-type] input').element.value).toBe(HistoryEventEntryType.SWAP_EVENT);
  });

  it('should emit the entry type the user picks', async () => {
    const wrapper = createWrapper({ nextSequenceId: '0', type: 'add' }, HistoryEventEntryType.HISTORY_EVENT);

    await wrapper.findComponent({ name: 'RuiMenuSelect' }).setValue(HistoryEventEntryType.EVM_SWAP_EVENT);

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([HistoryEventEntryType.EVM_SWAP_EVENT]);
  });

  it('should only offer the chain types when adding into an existing transaction', async () => {
    const wrapper = createWrapper({
      group: createMock<EvmHistoryEvent>({ entryType: HistoryEventEntryType.EVM_EVENT }),
      nextSequenceId: '2412',
      type: 'group-add',
    }, HistoryEventEntryType.EVM_EVENT);

    expect(await openOptions(wrapper)).toEqual([HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.EVM_SWAP_EVENT]);
  });

  it('should be locked while an event is edited', () => {
    const wrapper = createWrapper({
      event: createMock<EvmHistoryEvent>({ entryType: HistoryEventEntryType.EVM_EVENT }),
      nextSequenceId: '1',
      type: 'edit',
    }, HistoryEventEntryType.EVM_EVENT);

    expect(wrapper.findComponent({ name: 'RuiMenuSelect' }).props('disabled')).toBe(true);
  });
});
