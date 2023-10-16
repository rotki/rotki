import { type Wrapper, mount } from '@vue/test-utils';
import Vuetify from 'vuetify';
import { createPinia, setActivePinia } from 'pinia';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';

describe('EvmEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<HistoryEventForm>;

  const createWrapper = () => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(HistoryEventForm, {
      pinia,
      vuetify,
      stubs: {
        VSelect: {
          template: `
            <div>
              <input :value="value" class="input" type="text" @input="$emit('input', $event.value)">
            </div>
          `,
          props: {
            value: { type: String }
          }
        }
      }
    });
  };

  test('should show correct form based on the entryType', () => {
    wrapper = createWrapper();

    const entryTypeInput = wrapper.find('[data-cy="entry-type"] input');
    const entryTypeElement = entryTypeInput.element as HTMLInputElement;

    expect(entryTypeElement.value).toBe(HistoryEventEntryType.EVM_EVENT);
    expect(wrapper.find('[data-cy=evm-event-form]').exists()).toBeTruthy();

    Object.values(HistoryEventEntryType).forEach(async item => {
      await entryTypeInput.trigger('input', {
        value: item
      });
      await nextTick();
      const id = item.split(/ /g).join('-');
      expect(wrapper.find(`[data-cy=${id}-form]`).exists()).toBeTruthy();
    });
  });
});
