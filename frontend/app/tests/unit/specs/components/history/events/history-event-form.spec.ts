import { type VueWrapper, mount } from '@vue/test-utils';
import { createVuetify } from 'vuetify';
import { createPinia, setActivePinia } from 'pinia';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';
import VSelectStub from '../../../stubs/VSelect';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

describe('historyEventForm.vue', () => {
  setupDayjs();
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventForm>>;

  const createWrapper = () => {
    const vuetify = createVuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(HistoryEventForm, {
      global: {
        plugins: [
          pinia,
          vuetify,
        ],
        stubs: {
          VSelect: VSelectStub,
        },
      },
    });
  };

  it('should show correct form based on the entryType', () => {
    wrapper = createWrapper();

    const entryTypeInput = wrapper.find('[data-cy="entry-type"] input');
    const entryTypeElement = entryTypeInput.element as HTMLInputElement;

    expect(entryTypeElement.value).toBe(HistoryEventEntryType.HISTORY_EVENT);
    expect(wrapper.find('[data-cy=history-event-form]').exists()).toBeTruthy();

    Object.values(HistoryEventEntryType).forEach(async (item) => {
      await entryTypeInput.trigger('input', {
        value: item,
      });
      await nextTick(() => {
        const id = item.split(/ /g).join('-');
        expect(wrapper.find(`[data-cy=${id}-form]`).exists()).toBeTruthy();
      });
    });
  });
});
