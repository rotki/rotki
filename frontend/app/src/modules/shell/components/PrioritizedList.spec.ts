import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import { PrioritizedListData } from '@/modules/settings/types/prioritized-list-data';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';
import PrioritizedListEntry from '@/modules/shell/components/PrioritizedListEntry.vue';
import '@test/i18n';

describe('prioritized-list', () => {
  let wrapper: VueWrapper<InstanceType<typeof PrioritizedList>>;

  const entryOrderOf = (entries: VueWrapper<InstanceType<typeof PrioritizedListEntry>>[]): string[] => {
    const entryIds: string[] = [];
    entries.forEach((wrapper: VueWrapper<InstanceType<typeof PrioritizedListEntry>>) => {
      entryIds.push(wrapper.props().data.identifier);
    });
    return entryIds;
  };

  const emittedInputEventItems = (): string[] => {
    const emissions = wrapper.emitted<string[][]>('update:modelValue');
    expect(emissions).toHaveLength(1);
    return emissions![0][0];
  };

  const createWrapper = (options: ComponentMountingOptions<typeof PrioritizedList>): VueWrapper<InstanceType<typeof PrioritizedList>> => {
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

  it('should show all three items in correct order', () => {
    const elements = wrapper.findAllComponents(PrioritizedListEntry);
    expect(elements).toHaveLength(3);
    expect(entryOrderOf(elements)).toStrictEqual([AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ENS_NAMES, AddressNamePriority.ETHEREUM_TOKENS]);
  });

  it('should show "first up" and "last down" buttons disabled', () => {
    const firstUp = wrapper.find<HTMLInputElement>('#move-up-blockchain_account').element;
    expect(firstUp.disabled).toBe(true);
    const lastDown = wrapper.find<HTMLInputElement>('#move-down-ethereum_tokens').element;
    expect(lastDown.disabled).toBe(true);
  });

  it('should move entry up', async () => {
    const button = wrapper.find('#move-up-ens_names');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual([AddressNamePriority.ENS_NAMES, AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ETHEREUM_TOKENS]);
  });

  it('should move entry down', async () => {
    const button = wrapper.find('#move-down-ens_names');
    expect(button.exists()).toBe(true);
    await button.trigger('click');
    expect(emittedInputEventItems()).toStrictEqual([AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ETHEREUM_TOKENS, AddressNamePriority.ENS_NAMES]);
  });

  it('should delete entry', async () => {
    const button = wrapper.find('#delete-ens_names');
    expect(button.exists()).toBe(true);
    await button.trigger('click');

    expect(emittedInputEventItems()).toStrictEqual([AddressNamePriority.BLOCKCHAIN_ACCOUNT, AddressNamePriority.ETHEREUM_TOKENS]);
  });

  it('should show the save outcome in place', () => {
    const status = wrapper.find('[data-testid=prioritized-list-status]');

    // the error wins, since it is the one that needs acting on
    expect(status.text()).toContain('error message');
  });

  it('should warn inside the list once it is empty', async () => {
    await wrapper.setProps({ emptyWarning: 'nothing to price with', modelValue: [] });

    expect(wrapper.find('[data-testid=prioritized-list-empty-warning]').text()).toContain('nothing to price with');
  });

  it('should keep the plain empty state when there is no warning to give', async () => {
    await wrapper.setProps({ modelValue: [] });

    expect(wrapper.find('[data-testid=prioritized-list-empty-warning]').exists()).toBe(false);
  });

  describe('dismissing an error', () => {
    const error = (): ReturnType<typeof wrapper.find> => wrapper.find('[role=alert][data-testid=prioritized-list-status]');

    it('should hide the error once closed', async () => {
      await wrapper.find('[data-testid=prioritized-list-dismiss]').trigger('click');

      expect(error().exists()).toBe(false);
    });

    it('should show a different error that arrives after one was closed', async () => {
      await wrapper.find('[data-testid=prioritized-list-dismiss]').trigger('click');

      await wrapper.setProps({ status: { error: 'another failure', success: '' } });

      expect(error().text()).toContain('another failure');
    });

    it('should show the same error again after a new attempt cleared the last one', async () => {
      await wrapper.find('[data-testid=prioritized-list-dismiss]').trigger('click');
      await wrapper.setProps({ status: { error: '', success: '' } });

      await wrapper.setProps({ status: { error: 'error message', success: '' } });

      expect(error().text()).toContain('error message');
    });
  });
});
