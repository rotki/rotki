import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import AddressNamePrioritySetting from '@/modules/settings/frontend/AddressNamePrioritySetting.vue';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

const { useSettingModelMock } = vi.hoisted(() => ({ useSettingModelMock: vi.fn() }));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): { resetAddressesNames: () => void } => ({
    resetAddressesNames: vi.fn(),
  }),
}));
vi.mock('@/modules/settings/use-clearable-messages', () => ({
  useClearableMessages: (): Record<string, unknown> => ({
    clearAll: vi.fn(),
    error: ref<string>(''),
    setError: vi.fn(),
    setSuccess: vi.fn(),
    success: ref<boolean>(false),
  }),
}));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

describe('addressNamePrioritySetting', () => {
  beforeEach(() => {
    useSettingModelMock.mockReturnValue({
      error: ref<string>(''),
      model: ref<AddressNamePriority[]>([
        AddressNamePriority.ENS_NAMES,
        AddressNamePriority.PRIVATE_ADDRESSBOOK,
      ]),
      success: ref<boolean>(false),
    });
  });

  it('should allow adding GNS to the name priority order', () => {
    const prioritizedList = mount(AddressNamePrioritySetting, {
      global: {
        stubs: {
          ActionStatusIndicator: true,
          EnableEnsNamesSetting: true,
          PrioritizedListEntry: true,
          PrioritizedListRow: true,
        },
      },
    }).findComponent(PrioritizedList);

    expect(prioritizedList.exists()).toBe(true);
    expect(prioritizedList.props('disableAdd')).toBe(false);
    expect(prioritizedList.props('disableDelete')).toBe(true);
    expect(prioritizedList.props('allItems').itemIdsNotIn(prioritizedList.props('modelValue'))).toContain(AddressNamePriority.GNS_NAMES);
  });
});
