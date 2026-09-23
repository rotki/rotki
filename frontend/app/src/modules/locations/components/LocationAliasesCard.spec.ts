import type { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

type Aliases = ReturnType<typeof useLocationAliases>;

const { refreshAliases, removeAlias, saveAlias, show } = vi.hoisted(() => ({
  refreshAliases: vi.fn<Aliases['refreshAliases']>(),
  removeAlias: vi.fn<Aliases['removeAlias']>(),
  saveAlias: vi.fn<Aliases['saveAlias']>(),
  show: vi.fn(),
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

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    refreshAliases.mockResolvedValue(ok(undefined));
    removeAlias.mockResolvedValue(ok(undefined));
    useLocationTreeStore().setNodes([node('total', null, 'Total'), node('banks', 'total', 'Banks'), node('custom:ing', 'banks', 'ING', { isBuiltin: false })]);
    wrapper = mount(LocationAliasesCard, {
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
