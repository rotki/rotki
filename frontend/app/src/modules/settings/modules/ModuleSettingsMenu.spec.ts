import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { Module } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import ModuleSettingsMenu from '@/modules/settings/modules/ModuleSettingsMenu.vue';

const activeModules = ref<Module[]>([]);
const update = vi.fn(async (): Promise<void> => {});
const fetchQueriedAddresses = vi.fn(async (): Promise<void> => {});
const show = vi.fn();

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => activeModules),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({ update })),
}));

vi.mock('@/modules/accounts/use-queried-address-operations', () => ({
  useQueriedAddressOperations: vi.fn(() => ({ fetchQueriedAddresses })),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: vi.fn(() => ({ show })),
}));

const stubs = {
  AppImage: true,
  QueriedAddressDialog: {
    emits: ['close'],
    props: { module: { required: true, type: String } },
    template: '<div data-testid="queried-address-dialog" :data-module="module"><button data-testid="dialog-close" @click="$emit(\'close\')" /></div>',
  },
  RuiButton: {
    inheritAttrs: false,
    template: '<button v-bind="$attrs"><slot /></button>',
  },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div><slot /></div></div>',
  },
  RuiTooltip: { template: '<div><slot name="activator" /><span data-testid="tooltip"><slot /></span></div>' },
};

function createWrapper(props: { modules?: Module[]; attentionHint?: string } = {}, slot?: string): VueWrapper<InstanceType<typeof ModuleSettingsMenu>> {
  return mount(ModuleSettingsMenu, {
    global: { stubs },
    props: { modules: [Module.ETH2, Module.LIQUITY], ...props },
    slots: slot ? { default: slot } : {},
  });
}

function moduleRow(wrapper: VueWrapper, module: Module): ReturnType<VueWrapper['find']> {
  return wrapper.find(`[data-testid=module-settings-module][data-module=${module}]`);
}

async function openMenu(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=module-settings]').trigger('click');
  expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('true');
}

describe('modules/settings/modules/ModuleSettingsMenu', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(activeModules, [Module.ETH2]);
  });

  it('should fetch the queried addresses on mount', async () => {
    createWrapper();
    await flushPromises();

    expect(fetchQueriedAddresses).toHaveBeenCalledOnce();
  });

  it('should list each module the page depends on, by its name', () => {
    const wrapper = createWrapper();
    const rows = wrapper.findAll('[data-testid=module-settings-module]');

    expect(rows.map(row => row.attributes('data-module'))).toEqual([Module.ETH2, Module.LIQUITY]);
    expect(rows[0].text()).toContain('page_settings.module::ETH Staking');
    expect(rows[1].text()).toContain('page_settings.module::Liquity');
  });

  it('should offer address management for an enabled module and enabling for a disabled one', () => {
    const wrapper = createWrapper();

    expect(moduleRow(wrapper, Module.ETH2).find('[data-testid=module-settings-addresses]').exists()).toBe(true);
    expect(moduleRow(wrapper, Module.ETH2).find('[data-testid=module-settings-enable]').exists()).toBe(false);
    expect(moduleRow(wrapper, Module.LIQUITY).find('[data-testid=module-settings-enable]').exists()).toBe(true);
    expect(moduleRow(wrapper, Module.LIQUITY).find('[data-testid=module-settings-addresses]').exists()).toBe(false);
    expect(moduleRow(wrapper, Module.LIQUITY).text()).toContain('page_settings.disabled');
  });

  it('should say every address is queried when none is listed for the module', () => {
    const wrapper = createWrapper();

    expect(moduleRow(wrapper, Module.ETH2).text()).toContain('page_settings.all_addresses');
  });

  it('should count the addresses the module is limited to', async () => {
    const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
    const wrapper = createWrapper();
    set(queriedAddresses, { eth2: ['0x1', '0x2'] });
    await nextTick();

    expect(moduleRow(wrapper, Module.ETH2).text()).toContain('page_settings.some_addresses::2');
  });

  it('should close the menu and open the address dialog for the module, until it closes', async () => {
    const wrapper = createWrapper();
    await openMenu(wrapper);
    expect(wrapper.find('[data-testid=queried-address-dialog]').exists()).toBe(false);

    await moduleRow(wrapper, Module.ETH2).find('[data-testid=module-settings-addresses]').trigger('click');

    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
    expect(wrapper.find('[data-testid=queried-address-dialog]').attributes('data-module')).toBe(Module.ETH2);

    await wrapper.find('[data-testid=dialog-close]').trigger('click');

    expect(wrapper.find('[data-testid=queried-address-dialog]').exists()).toBe(false);
  });

  it('should close the menu and confirm before enabling a module, keeping the active ones', async () => {
    const wrapper = createWrapper();
    await openMenu(wrapper);
    await moduleRow(wrapper, Module.LIQUITY).find('[data-testid=module-settings-enable]').trigger('click');

    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
    expect(show).toHaveBeenCalledOnce();
    expect(show.mock.calls[0][0]).toEqual({
      message: 'active_modules.enable.description::Liquity',
      title: 'active_modules.enable.title',
      type: 'info',
    });
    expect(update).not.toHaveBeenCalled();

    await show.mock.calls[0][1]();

    expect(update).toHaveBeenCalledWith({ activeModules: [Module.ETH2, Module.LIQUITY] });
  });

  it('should mark the button and explain why while something wants a look', () => {
    const wrapper = createWrapper({ attentionHint: 'An API key is waiting' });

    expect(wrapper.find('[data-testid=module-settings-attention]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=module-settings]').attributes('aria-description')).toBe('An API key is waiting');
    expect(wrapper.find('[data-testid=tooltip]').text()).toContain('An API key is waiting');
  });

  it('should show no mark without an attention hint', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=module-settings-attention]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=tooltip]').text()).toBe('page_settings.title');
  });

  it('should show what the page adds below the modules', () => {
    const wrapper = createWrapper({}, '<span data-testid="page-extra" />');

    expect(wrapper.find('[data-testid=page-extra]').exists()).toBe(true);
  });
});
