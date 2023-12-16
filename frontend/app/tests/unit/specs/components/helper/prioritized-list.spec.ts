import { type ComponentMountingOptions, type VueWrapper, mount } from '@vue/test-utils';
import { expect } from 'vitest';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import { PrioritizedListData } from '@/types/settings/prioritized-list-data';
import '../../../i18n';

describe('prioritizedList.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof PrioritizedList>>;

  const entryOrderOf = (entries: VueWrapper<InstanceType<typeof PrioritizedListEntry>>[]): string[] => {
    const entryIds: string[] = [];
    entries.forEach((wrapper: VueWrapper<InstanceType<typeof PrioritizedListEntry>>) => {
      entryIds.push(wrapper.props().data.identifier);
    });
    return entryIds;
  };

  const emittedInputEventItems = (): string[] => {
    expect(wrapper.emitted()['update:model-value'].length).toBe(1);
    const emitted = wrapper.emitted()['update:model-value'][0];
    return emitted[0];
  };

  const createWrapper = (options: ComponentMountingOptions<typeof PrioritizedList>) => {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(PrioritizedList, {
      global: {
        plugins: [pinia],
        stubs: ['action-status-indicator'],
      },
      ...options,
    });
  };

  beforeEach(() => {
    const allItems = new PrioritizedListData([
      { identifier: 'value1' },
      { identifier: 'value2' },
      { identifier: 'value3' },
      { identifier: 'value4' },
    ]);
    wrapper = createWrapper({
      props: {
        modelValue: ['value1', 'value2', 'value3'],
        allItems,
        itemDataName: 'item data',
        disableAdd: false,
        disableDelete: false,
        status: {
          success: 'success message',
          error: 'error message',
        },
      },
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('show all three items in correct order', () => {
    const elements = wrapper.findAllComponents(PrioritizedListEntry);
    expect(elements.length).toBe(3);
    expect(entryOrderOf(elements)).toStrictEqual(['value1', 'value2', 'value3']);
  });

  it('show "first up" and "last down" buttons disabled', () => {
    const firstUp = wrapper.find('#move-up-value1');
    expect(firstUp.element.disabled).toBe(true);
    const lastDown = wrapper.find('#move-down-value3');
    expect(lastDown.element.disabled).toBe(true);
  });

  it('move entry up', async () => {
    const button = wrapper.find('#move-up-value2');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual(['value2', 'value1', 'value3']);
  });

  it('move entry down', async () => {
    const button = wrapper.find('#move-down-value2');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual(['value1', 'value3', 'value2']);
  });

  it('delete entry', async () => {
    const button = wrapper.find('#delete-value2');
    expect(button.exists()).toBe(true);
    await button.trigger('click');

    expect(emittedInputEventItems()).toStrictEqual(['value1', 'value3']);
  });
});
