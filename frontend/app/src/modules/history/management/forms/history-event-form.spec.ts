import type { EvmHistoryEvent } from '@/types/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';
import { isEvmTypeEvent } from '@/modules/history/management/forms/form-guards';
import { setupDayjs } from '@/utils/date';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

const formTypesYouCanAddTo = Object.values(HistoryEventEntryType).filter(type => !isEvmTypeEvent(type));

type Wrapper = VueWrapper<InstanceType<typeof HistoryEventForm>>;

async function createWrapper(
  options: ComponentMountingOptions<typeof HistoryEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  },
): Promise<Wrapper> {
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
    ...options,
  });
  await vi.advanceTimersToNextTimerAsync();
  return wrapper;
}

describe('component/HistoryEventForm.vue', () => {
  let wrapper: Wrapper;

  beforeAll(() => {
    setupDayjs();
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  it('should default to history event form', async () => {
    expect.assertions(2);

    wrapper = await createWrapper();
    const entryTypeInput = wrapper.find('[data-cy=entry-type] input');
    const entryTypeElement = entryTypeInput.element as HTMLInputElement;

    expect(entryTypeElement.value).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(wrapper.find('[data-cy=history-event-form]').exists()).toBeTruthy();
  });

  it.each(formTypesYouCanAddTo)('changes to proper form %s', async (value: string) => {
    wrapper = await createWrapper();
    await wrapper.find('[data-cy=entry-type] [data-id=activator]').trigger('click');
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
    expect(wrapper.find(`[data-cy=${id}-form]`).exists(), `id: ${id}`).toBeTruthy();
  });

  it('should only allow two options on an existing transaction', async () => {
    const group: EvmHistoryEvent = {
      address: '0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C',
      amount: bigNumberify(5),
      asset: 'ETH',
      counterparty: null,
      entryType: HistoryEventEntryType.EVM_EVENT,
      eventIdentifier: '10x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
      eventSubtype: '',
      eventType: 'receive',
      identifier: 14344,
      location: 'ethereum',
      locationLabel: '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
      sequenceIndex: 2411,
      timestamp: 1686495083,
      txHash: '0x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
      userNotes: '',
    };
    wrapper = await createWrapper({
      props: {
        data: {
          group,
          nextSequenceId: '2412',
          type: 'group-add',
        },
      },
    });
    await wrapper.find('[data-cy=entry-type] [data-id=activator]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const options = wrapper.find('[role="menu-content"]').findAll('button');
    expect(options).toHaveLength(2);
    expect(options.at(0)!.text()).toBe(HistoryEventEntryType.EVM_EVENT);
    expect(options.at(1)!.text()).toBe(HistoryEventEntryType.EVM_SWAP_EVENT);
  });
});
