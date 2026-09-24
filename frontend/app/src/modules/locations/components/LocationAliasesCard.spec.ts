import type { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

type Aliases = ReturnType<typeof useLocationAliases>;

const { refreshAliases, removeAlias, saveAlias, setMessage, show } = vi.hoisted(() => ({
  refreshAliases: vi.fn<Aliases['refreshAliases']>(),
  removeAlias: vi.fn<Aliases['removeAlias']>(),
  saveAlias: vi.fn<Aliases['saveAlias']>(),
  setMessage: vi.fn(),
  show: vi.fn(),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/locations/use-location-aliases', () => ({
  useLocationAliases: (): Partial<Aliases> => ({
    aliases: ref([{ alias: 'ING DIBA', locationIdentifier: 'custom:ing' }]),
    loading: ref(false),
    refreshAliases,
    removeAlias,
    saveAlias,
  }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

describe('locationAliasesCard', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LocationAliasesCard>>;

  function mountCard(): VueWrapper<InstanceType<typeof LocationAliasesCard>> {
    return mount(LocationAliasesCard, {
      global: {
        plugins: [pinia],
        stubs: {
          LocationIcon: true,
          LocationSelector: true,
          RuiDataTable: {
            props: ['rows'],
            template: '<div><div v-for="row in rows" :key="row.alias" data-testid="alias-row"><slot name="item.locationIdentifier" :row="row" /><slot name="item.actions" :row="row" /></div></div>',
          },
        },
      },
    });
  }

  async function fillAlias(alias: string, target: string): Promise<void> {
    await wrapper.find('[data-testid=location-alias-name] input').setValue(alias);
    wrapper.findComponent({ name: 'LocationSelector' }).vm.$emit('update:modelValue', target);
    await nextTick();
  }

  function saveButton(): ReturnType<VueWrapper['find']> {
    return wrapper.find('[data-testid=location-alias-save]');
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    refreshAliases.mockResolvedValue(ok(undefined));
    removeAlias.mockResolvedValue(ok(undefined));
    saveAlias.mockResolvedValue(ok(undefined));
    useLocationTreeStore().setNodes([node('total', null, 'Total'), node('banks', 'total', 'Banks'), node('custom:ing', 'banks', 'ING', { isBuiltin: false })]);
    wrapper = mountCard();
  });

  it('should keep save disabled until both an alias and a location are given', async () => {
    expect(saveButton().attributes('disabled')).toBeDefined();

    await wrapper.find('[data-testid=location-alias-name] input').setValue('   ');
    wrapper.findComponent({ name: 'LocationSelector' }).vm.$emit('update:modelValue', 'custom:ing');
    await nextTick();
    expect(saveButton().attributes('disabled')).toBeDefined();

    await wrapper.find('[data-testid=location-alias-name] input').setValue('ing-diba');
    expect(saveButton().attributes('disabled')).toBeUndefined();
  });

  it('should save the alias and clear the form for the next one', async () => {
    await fillAlias('ing-diba', 'custom:ing');

    await wrapper.find('[data-testid=location-alias-form]').trigger('submit');
    await flushPromises();

    expect(saveAlias).toHaveBeenCalledExactlyOnceWith('ing-diba', 'custom:ing');
    expect(wrapper.find<HTMLInputElement>('[data-testid=location-alias-name] input').element.value).toBe('');
    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  it('should report a refused alias and keep what the user typed', async () => {
    saveAlias.mockResolvedValue(err('Location custom:ing is archived'));
    await fillAlias('ing-diba', 'custom:ing');

    await wrapper.find('[data-testid=location-alias-form]').trigger('submit');
    await flushPromises();

    expect(setMessage).toHaveBeenCalledExactlyOnceWith({ description: 'Location custom:ing is archived', title: 'location_manager.aliases.error' });
    expect(wrapper.find<HTMLInputElement>('[data-testid=location-alias-name] input').element.value).toBe('ing-diba');
  });

  it('should report aliases that could not be loaded', async () => {
    refreshAliases.mockResolvedValue(err('backend down'));

    mountCard();
    await flushPromises();

    expect(setMessage).toHaveBeenCalledExactlyOnceWith({ description: 'backend down', title: 'location_manager.aliases.error' });
  });

  it('should report an alias delete that failed', async () => {
    removeAlias.mockResolvedValue(err('Location alias ING DIBA does not exist'));
    await wrapper.find('[data-testid=location-alias-delete]').trigger('click');

    await show.mock.calls[0][1]();

    expect(setMessage).toHaveBeenCalledExactlyOnceWith({ description: 'Location alias ING DIBA does not exist', title: 'location_manager.aliases.error' });
  });

  it('should show the path of the location an alias points at', async () => {
    await flushPromises();
    expect(wrapper.find('[data-testid=alias-row]').text()).toContain('Banks › ING');
  });

  it('should only delete an alias once confirmed', async () => {
    await wrapper.find('[data-testid=location-alias-delete]').trigger('click');
    expect(removeAlias).not.toHaveBeenCalled();
    expect(show.mock.calls[0][0].message).toBe('location_manager.aliases.delete_message::ING DIBA, Banks › ING');

    await show.mock.calls[0][1]();
    expect(removeAlias).toHaveBeenCalledExactlyOnceWith('ING DIBA');
  });
});
