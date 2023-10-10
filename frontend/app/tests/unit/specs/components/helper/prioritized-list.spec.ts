import {
  type ThisTypedMountOptions,
  type Wrapper,
  type WrapperArray,
  mount
} from '@vue/test-utils';
import { PiniaVuePlugin } from 'pinia';
import { expect } from 'vitest';
import Vue from 'vue';
import Vuetify from 'vuetify';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import { PrioritizedListData } from '@/types/settings/prioritized-list-data';
import '../../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('PrioritizedList.vue', () => {
  let wrapper: Wrapper<any>;

  const createWrapper = (options: ThisTypedMountOptions<any>) => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PrioritizedList, {
      pinia,
      vuetify,
      stubs: ['action-status-indicator'],
      ...options
    });
  };

  beforeEach(() => {
    const allItems = new PrioritizedListData([
      { identifier: 'value1' },
      { identifier: 'value2' },
      { identifier: 'value3' },
      { identifier: 'value4' }
    ]);
    wrapper = createWrapper({
      propsData: {
        value: ['value1', 'value2', 'value3'],
        allItems,
        itemDataName: 'item data',
        disableAdd: false,
        disableDelete: false,
        status: {
          success: 'success message',
          error: 'error message'
        }
      }
    });
  });

  test('show all three items in correct order', () => {
    const elements = wrapper.findAllComponents(PrioritizedListEntry);
    expect(elements.length).toBe(3);
    expect(entryOrderOf(elements)).toStrictEqual([
      'value1',
      'value2',
      'value3'
    ]);
  });

  test('show "first up" and "last down" buttons disabled', () => {
    const firstUp = wrapper.find('#move-up-value1');
    expect(firstUp.element.disabled).toBe(true);
    const lastDown = wrapper.find('#move-down-value3');
    expect(lastDown.element.disabled).toBe(true);
  });

  test('move entry up', async () => {
    const button = wrapper.find('#move-up-value2');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual([
      'value2',
      'value1',
      'value3'
    ]);
  });

  test('move entry down', async () => {
    const button = wrapper.find('#move-down-value2');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual([
      'value1',
      'value3',
      'value2'
    ]);
  });

  test('delete entry', async () => {
    const button = wrapper.find('#delete-value2');
    expect(button.exists()).toBe(true);
    await button.trigger('click');

    expect(emittedInputEventItems()).toStrictEqual(['value1', 'value3']);
  });

  const entryOrderOf = (
    entries: WrapperArray<PrioritizedListEntry>
  ): string[] => {
    const entryIds: string[] = [];
    entries.wrappers.forEach(
      (wrapper: Wrapper<PrioritizedListEntry, Element>) => {
        entryIds.push(wrapper.props().data.identifier);
      }
    );
    return entryIds;
  };

  const emittedInputEventItems = (): string[] => {
    // @ts-ignore
    expect(wrapper.emitted().input.length).toBe(1);
    // @ts-ignore
    const emitted = wrapper.emitted().input[0];
    return emitted[0];
  };
});
