import type { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

type Aliases = ReturnType<typeof useLocationAliases>;

const { refreshAliases, removeAlias, saveAlias } = vi.hoisted(() => ({
  refreshAliases: vi.fn<Aliases['refreshAliases']>(),
  removeAlias: vi.fn<Aliases['removeAlias']>(),
  saveAlias: vi.fn<Aliases['saveAlias']>(),
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

describe('locationAliasesCard', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LocationAliasesCard>>;

  function mountCard(): VueWrapper<InstanceType<typeof LocationAliasesCard>> {
    return mount(LocationAliasesCard, {
      global: {
        plugins: [pinia],
        stubs: {
          PillFilterBar: { emits: ['update:params'], name: 'PillFilterBar', props: ['params', 'fields', 'labels'], template: '<div />' },
          LocationAliasFormDialog: { name: 'LocationAliasFormDialog', props: ['modelValue', 'aliases', 'save'], template: '<div />' },
          LocationIcon: true,
          RuiDataTable: {
            name: 'RuiDataTable',
            props: ['rows', 'empty'],
            template: '<div><slot name="body.prepend" /><div v-for="row in rows" :key="row.alias" data-testid="alias-row"><slot name="item.locationIdentifier" :row="row" /><slot name="item.actions" :row="row" /></div></div>',
          },
        },
      },
      props: { adding: false },
    });
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

  it('should hand the form the save that updates the list', () => {
    expect(wrapper.findComponent({ name: 'LocationAliasFormDialog' }).props('save')).toBe(saveAlias);
  });

  it('should open the form when the page asks to add an alias', async () => {
    expect(wrapper.findComponent({ name: 'LocationAliasFormDialog' }).props('modelValue')).toBe(false);
    await wrapper.setProps({ adding: true });
    expect(wrapper.findComponent({ name: 'LocationAliasFormDialog' }).props('modelValue')).toBe(true);
  });

  it('should list only the aliases that match the filter', async () => {
    await flushPromises();
    const filter = wrapper.findComponent({ name: 'PillFilterBar' });
    filter.vm.$emit('update:params', { alias: 'diba' });
    await nextTick();
    expect(wrapper.findAll('[data-testid=alias-row]')).toHaveLength(1);

    filter.vm.$emit('update:params', { alias: 'luno' });
    await nextTick();
    expect(wrapper.findAll('[data-testid=alias-row]')).toHaveLength(0);
    expect(wrapper.findComponent({ name: 'RuiDataTable' }).props('empty')).toEqual({ label: 'location_manager.aliases.empty_search_label' });

    filter.vm.$emit('update:params', { location: 'custom:other' });
    await nextTick();
    expect(wrapper.findAll('[data-testid=alias-row]')).toHaveLength(0);

    filter.vm.$emit('update:params', { location: 'custom:ing' });
    await nextTick();
    expect(wrapper.findAll('[data-testid=alias-row]')).toHaveLength(1);
  });

  it('should name aliases that could not be loaded above the ones still listed, with a retry', async () => {
    refreshAliases.mockResolvedValueOnce(err('backend down')).mockResolvedValueOnce(ok(undefined));

    wrapper = mountCard();
    await flushPromises();

    const failure = wrapper.find('[data-testid=location-aliases-load-error]');
    expect(failure.text()).toContain('backend down');
    await failure.find('[data-testid=failure-strip-retry]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid=location-aliases-load-error]').exists()).toBe(false);
  });

  it('should report an alias delete that failed', async () => {
    removeAlias.mockResolvedValue(err('Location alias ING DIBA does not exist'));
    await wrapper.find('[data-testid=location-alias-delete]').trigger('click');
    await wrapper.find('[data-testid=location-alias-confirm-delete]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid=location-aliases-action-error]').text()).toContain('Location alias ING DIBA does not exist');
  });

  it('should show the path of the location an alias points at', async () => {
    await flushPromises();
    expect(wrapper.find('[data-testid=alias-row]').text()).toContain('Banks › ING');
  });

  it('should only delete an alias once confirmed in its row', async () => {
    await wrapper.find('[data-testid=location-alias-delete]').trigger('click');
    expect(removeAlias).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=location-alias-confirm]').exists()).toBe(true);

    await wrapper.find('[data-testid=location-alias-cancel-delete]').trigger('click');
    expect(wrapper.find('[data-testid=location-alias-confirm]').exists()).toBe(false);
    expect(removeAlias).not.toHaveBeenCalled();

    await wrapper.find('[data-testid=location-alias-delete]').trigger('click');
    await wrapper.find('[data-testid=location-alias-confirm-delete]').trigger('click');
    expect(removeAlias).toHaveBeenCalledExactlyOnceWith('ING DIBA');
  });
});
