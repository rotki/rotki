import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LocationTreeRowActions from '@/modules/locations/components/LocationTreeRowActions.vue';
import '@test/i18n';

const isSmAndDown = ref<boolean>(false);

vi.mock('@rotki/ui-library', async () => {
  const actual = await vi.importActual<typeof import('@rotki/ui-library')>('@rotki/ui-library');
  return { ...actual, useBreakpoint: (): Record<string, unknown> => ({ isSmAndDown }) };
});

const custom = node('custom:ing', 'banks', 'ING', { isBuiltin: false });

function createWrapper(location: LocationNode): VueWrapper<InstanceType<typeof LocationTreeRowActions>> {
  return mount(LocationTreeRowActions, {
    global: { stubs: { RuiMenu: { template: '<div data-testid="menu"><slot name="activator" :attrs="{}" /><slot /></div>' } } },
    props: { node: location },
  });
}

function slotTestIds(wrapper: VueWrapper): (string | undefined)[] {
  return wrapper.findAll('.grid > *').map(slot => slot.attributes('data-testid'));
}

describe('locationTreeRowActions', () => {
  beforeEach(() => {
    set(isSmAndDown, false);
  });

  it('should keep every action in its own column, leaving the slots that do not apply empty', () => {
    expect(slotTestIds(createWrapper(node('banks', 'total', 'Banks')))).toEqual(['location-add-child', undefined, undefined, undefined]);
    expect(slotTestIds(createWrapper(custom))).toEqual(['location-add-child', 'location-toggle-archive', 'row-edit', 'row-delete']);
  });

  it('should offer a restore instead of adding below an archived location', () => {
    const wrapper = createWrapper({ ...custom, isActive: false });
    expect(slotTestIds(wrapper)[0]).toBeUndefined();
    expect(wrapper.find('[data-testid=location-toggle-archive]').attributes('title')).toBe('location_manager.actions.unarchive');
  });

  it('should emit the action that was clicked', async () => {
    const wrapper = createWrapper(custom);
    await wrapper.find('[data-testid=row-delete]').trigger('click');
    await wrapper.find('[data-testid=location-add-child]').trigger('click');
    expect(Object.keys(wrapper.emitted())).toEqual(expect.arrayContaining(['delete', 'add-child']));
    expect(wrapper.emitted('edit')).toBeUndefined();
  });

  it('should fold the actions of a custom location into a menu on a small screen', () => {
    set(isSmAndDown, true);
    const wrapper = createWrapper(custom);
    expect(wrapper.find('[data-testid=location-row-menu]').exists()).toBe(true);
    expect(wrapper.find('.grid').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid=menu] [data-testid]').map(item => item.attributes('data-testid')))
      .toEqual(expect.arrayContaining(['location-add-child', 'location-toggle-archive', 'row-edit', 'row-delete']));
  });

  it('should keep a lone action as a plain button on a small screen', () => {
    set(isSmAndDown, true);
    const wrapper = createWrapper(node('banks', 'total', 'Banks'));
    expect(wrapper.find('[data-testid=location-row-menu]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=location-add-child]').exists()).toBe(true);
  });
});
