import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ModuleActivator from '@/modules/accounts/ModuleActivator.vue';
import { Module } from '@/modules/core/common/modules';

const { activeModules } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { activeModules: ref<string[]>([]) };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => activeModules),
}));

vi.mock('@/modules/accounts/use-queried-address-operations', () => ({
  useQueriedAddressOperations: (): Record<string, unknown> => ({
    fetchQueriedAddresses: vi.fn<() => Promise<void>>(async () => Promise.resolve()),
  }),
}));

vi.mock('@/modules/accounts/use-account-loading', async () => {
  const { computed } = await import('vue');
  return {
    useAccountLoading: (): Record<string, unknown> => ({
      isAccountOperationRunning: () => computed<boolean>(() => false),
    }),
  };
});

function createWrapper(selection: Module[] = []): VueWrapper<InstanceType<typeof ModuleActivator>> {
  return mount(ModuleActivator, {
    global: { stubs: { AppImage: true } },
    props: { selection },
  });
}

function moduleButton(wrapper: VueWrapper, module: Module): ReturnType<VueWrapper['find']> {
  return wrapper.find(`[data-testid=module-activator-module][data-module=${module}]`);
}

describe('moduleActivator', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(activeModules, []);
  });

  it('should emit update:selection with the module whose button was toggled on', async () => {
    const wrapper = createWrapper();

    await moduleButton(wrapper, Module.LIQUITY).trigger('click');

    expect(wrapper.emitted('update:selection')).toEqual([[[Module.LIQUITY]]]);
  });

  it('should emit update:selection without the module whose button was toggled off', async () => {
    const wrapper = createWrapper([Module.LIQUITY, Module.ETH2]);

    await moduleButton(wrapper, Module.LIQUITY).trigger('click');

    expect(wrapper.emitted('update:selection')).toEqual([[[Module.ETH2]]]);
  });
});
