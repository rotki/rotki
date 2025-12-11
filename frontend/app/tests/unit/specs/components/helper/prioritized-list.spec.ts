import type { PrioritizedListId } from '@/types/settings/prioritized-list-id';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import { AddressNamePriority } from '@/types/settings/address-name-priorities';
import { PrioritizedListData } from '@/types/settings/prioritized-list-data';
import '@test/i18n';

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
    expect(wrapper.emitted()['update:modelValue'].length).toBe(1);
    const emitted = wrapper.emitted()['update:modelValue'][0] as string[][];
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
    const allItems = new PrioritizedListData<PrioritizedListId>([
      { identifier: AddressNamePriority.BLOCKCHAIN_ACCOUNT },
      { identifier: AddressNamePriority.ENS_NAMES },
      { identifier: AddressNamePriority.ETHEREUM_TOKENS },
      { identifier: AddressNamePriority.GLOBAL_ADDRESSBOOK },
    ]);
    wrapper = createWrapper({
      props: {
        modelValue: [
          AddressNamePriority.BLOCKCHAIN_ACCOUNT,
          AddressNamePriority.ENS_NAMES,
          AddressNamePriority.ETHEREUM_TOKENS,
        ],
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
    expect(entryOrderOf(elements)).toStrictEqual([AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ENS_NAMES, AddressNamePriority.ETHEREUM_TOKENS]);
  });

  it('show "first up" and "last down" buttons disabled', () => {
    const firstUp = wrapper.find('#move-up-blockchain_account').element as HTMLInputElement;
    expect(firstUp.disabled).toBe(true);
    const lastDown = wrapper.find('#move-down-ethereum_tokens').element as HTMLInputElement;
    expect(lastDown.disabled).toBe(true);
  });

  it('move entry up', async () => {
    const button = wrapper.find('#move-up-ens_names');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual([AddressNamePriority.ENS_NAMES, AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ETHEREUM_TOKENS]);
  });

  it('move entry down', async () => {
    const button = wrapper.find('#move-down-ens_names');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual([AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ETHEREUM_TOKENS, AddressNamePriority.ENS_NAMES]);
  });

  it('delete entry', async () => {
    const button = wrapper.find('#delete-ens_names');
    expect(button.exists()).toBe(true);
    await button.trigger('click');

    expect(emittedInputEventItems()).toStrictEqual([AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ETHEREUM_TOKENS]);
  });
});
