import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import LocationAliasFormDialog from '@/modules/locations/components/LocationAliasFormDialog.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  name: 'BigDialog',
  props: { action: { default: undefined, type: Object }, display: { default: false, type: Boolean } },
  setup: (props, { slots }) => (): VNode => h('div', {
    'data-disabled': String(props.action?.disabled ?? false),
    'data-primary': props.action?.primary,
  }, slots.default?.()),
});

const LocationSelectorStub = defineComponent({
  emits: ['update:modelValue'],
  name: 'LocationSelector',
  props: { modelValue: { default: '', type: String } },
  setup: () => (): VNode => h('div'),
});

const RuiAlertStub = { props: ['type'], template: '<div :data-type="type"><slot /></div>' };

const save = vi.fn<(alias: string, locationIdentifier: string) => Promise<string | undefined>>();

describe('locationAliasFormDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof LocationAliasFormDialog>>;

  function createWrapper(): VueWrapper<InstanceType<typeof LocationAliasFormDialog>> {
    return mount(LocationAliasFormDialog, {
      global: { stubs: { BigDialog: BigDialogStub, LocationSelector: LocationSelectorStub, RuiAlert: RuiAlertStub } },
      props: {
        'aliases': [{ alias: 'luno', locationIdentifier: 'custom:harbor' }],
        'modelValue': true,
        'onUpdate:modelValue': async (value: boolean): Promise<void> => wrapper.setProps({ modelValue: value }),
        save,
      },
    });
  }

  async function fill(alias: string, target: string): Promise<void> {
    await wrapper.find('[data-testid=location-alias-name] input').setValue(alias);
    wrapper.findComponent(LocationSelectorStub).vm.$emit('update:modelValue', target);
    await flushPromises();
  }

  function dialog(): VueWrapper<InstanceType<typeof BigDialogStub>> {
    return wrapper.findComponent(BigDialogStub);
  }

  async function confirm(): Promise<void> {
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();
  }

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    save.mockResolvedValue(undefined);
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('exchanges', 'total', 'Exchanges'),
      node('custom:harbor', 'exchanges', 'Harbor OTC', { isBuiltin: false }),
      node('custom:pier', 'exchanges', 'Pier Account', { isBuiltin: false }),
    ]);
    wrapper = createWrapper();
  });

  it('should keep save disabled until both an alias and a location are given', async () => {
    expect(dialog().attributes('data-disabled')).toBe('true');

    await fill('cex', '');
    expect(dialog().attributes('data-disabled')).toBe('true');

    await fill('   ', 'custom:pier');
    expect(dialog().attributes('data-disabled')).toBe('true');

    await fill('cex', 'custom:pier');
    expect(dialog().attributes('data-disabled')).toBe('false');
  });

  it('should save a new alias and close', async () => {
    await fill('cex', 'custom:pier');
    expect(dialog().attributes('data-primary')).toBe('location_manager.aliases.add');
    expect(wrapper.find('[data-testid=location-alias-existing]').exists()).toBe(false);

    await confirm();

    expect(save).toHaveBeenCalledExactlyOnceWith('cex', 'custom:pier');
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
  });

  it('should warn that an existing alias moves, matching it without case', async () => {
    await fill('LUNO', 'custom:pier');

    const notice = wrapper.find('[data-testid=location-alias-existing]');
    expect(notice.attributes('data-type')).toBe('warning');
    expect(notice.text()).toBe('location_manager.aliases.move_notice::luno, Exchanges › Harbor OTC');
    expect(dialog().attributes('data-primary')).toBe('location_manager.aliases.move');
  });

  it('should not save an alias that already points at the chosen location', async () => {
    await fill('luno', 'custom:harbor');

    expect(wrapper.find('[data-testid=location-alias-existing]').attributes('data-type')).toBe('info');
    expect(dialog().attributes('data-disabled')).toBe('true');
    await confirm();
    expect(save).not.toHaveBeenCalled();
  });

  it('should stay open and show why a save was refused', async () => {
    save.mockResolvedValue('Location custom:pier is archived');
    await fill('cex', 'custom:pier');

    await confirm();

    expect(wrapper.find('[data-testid=location-alias-form-error]').text()).toContain('Location custom:pier is archived');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should start empty each time it opens', async () => {
    await fill('cex', 'custom:pier');
    await wrapper.setProps({ modelValue: false });
    await wrapper.setProps({ modelValue: true });

    expect(wrapper.find<HTMLInputElement>('[data-testid=location-alias-name] input').element.value).toBe('');
    expect(wrapper.findComponent(LocationSelectorStub).props('modelValue')).toBe('');
  });
});
