import type { useLocationManagement } from '@/modules/locations/use-location-management';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import LocationManager from '@/modules/locations/components/LocationManager.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

type Management = ReturnType<typeof useLocationManagement>;

const { deleteLocation, editLocation, fetchUsage, setMessage, show } = vi.hoisted(() => ({
  deleteLocation: vi.fn<Management['deleteLocation']>(),
  editLocation: vi.fn<Management['editLocation']>(),
  fetchUsage: vi.fn<Management['fetchUsage']>(),
  setMessage: vi.fn(),
  show: vi.fn(),
}));

vi.mock('@/modules/locations/use-location-management', () => ({
  useLocationManagement: (): Partial<Management> => ({ deleteLocation, editLocation, fetchUsage }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('vue-router', () => ({
  useRoute: (): unknown => ref({ query: {} }),
  useRouter: (): Record<string, unknown> => ({ replace: vi.fn() }),
}));

describe('locationManager', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LocationManager>>;

  function createWrapper(): VueWrapper<InstanceType<typeof LocationManager>> {
    return mount(LocationManager, {
      global: {
        plugins: [pinia],
        stubs: {
          LocationAliasesCard: true,
          LocationFormDialog: true,
          LocationIcon: { props: ['item'], template: '<span>{{ item }}</span>' },
          RuiDataTable: {
            props: ['rows'],
            template: '<div><div v-for="row in rows" :key="row.path" data-testid="table-row"><slot name="item.name" :row="row" /><slot name="item.actions" :row="row" /></div></div>',
          },
          RuiDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
          TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  function row(identifier: string): ReturnType<VueWrapper['findAll']>[number] | undefined {
    return wrapper.findAll('[data-testid=table-row]').find(item => item.find(`[data-location="${identifier}"]`).exists());
  }

  function actionsOf(identifier: string): ReturnType<VueWrapper['findAll']>[number] {
    const tableRow = row(identifier);
    assert(tableRow);
    return tableRow;
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('banks', 'total', 'Banks'),
      node('custom:ing', 'banks', 'ING', { isBuiltin: false }),
      node('custom:closed', 'banks', 'Closed', { isActive: false, isBuiltin: false }),
    ]);
    editLocation.mockResolvedValue(ok({ location: node('custom:ing', 'banks', 'ING'), newPath: [], oldPath: [] }));
  });

  it('should list the tree without archived locations until asked', async () => {
    wrapper = createWrapper();
    expect(row('custom:ing')).toBeDefined();
    expect(row('custom:closed')).toBeUndefined();
    await wrapper.find('[data-testid=location-manager-show-archived] input').setValue(true);
    expect(row('custom:closed')).toBeDefined();
  });

  it('should only let custom locations be edited, archived or deleted', () => {
    wrapper = createWrapper();
    expect(actionsOf('banks').find('[data-testid=location-toggle-archive]').exists()).toBe(false);
    expect(actionsOf('custom:ing').find('[data-testid=location-toggle-archive]').exists()).toBe(true);
  });

  it('should show what uses a location instead of deleting it, and archive it from there', async () => {
    fetchUsage.mockResolvedValue(ok({ deletable: false, usage: { history_events: 3 } }));
    wrapper = createWrapper();

    await actionsOf('custom:ing').find('[data-testid=row-delete]').trigger('click');
    await flushPromises();

    expect(show).not.toHaveBeenCalled();
    expect(deleteLocation).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=location-usage-entry]').text()).toContain('3');
    await wrapper.find('[data-testid=location-usage-archive]').trigger('click');
    expect(editLocation).toHaveBeenCalledExactlyOnceWith('custom:ing', { isActive: false });
  });

  it('should delete an unused location once confirmed', async () => {
    fetchUsage.mockResolvedValue(ok({ deletable: true, usage: {} }));
    deleteLocation.mockResolvedValue(ok(true));
    wrapper = createWrapper();

    await actionsOf('custom:ing').find('[data-testid=row-delete]').trigger('click');
    await flushPromises();
    expect(deleteLocation).not.toHaveBeenCalled();
    await show.mock.calls[0][1]();

    expect(deleteLocation).toHaveBeenCalledExactlyOnceWith('custom:ing');
  });

  it('should report a failed usage check instead of deleting', async () => {
    fetchUsage.mockResolvedValue(err('offline'));
    wrapper = createWrapper();

    await actionsOf('custom:ing').find('[data-testid=row-delete]').trigger('click');
    await flushPromises();

    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'offline' }));
    expect(show).not.toHaveBeenCalled();
  });
});
