import type { LocationRow } from '@/modules/locations/location-rows';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LocationTreeRowName from '@/modules/locations/components/LocationTreeRowName.vue';
import '@test/i18n';

function row(overrides: Partial<LocationRow> = {}): LocationRow {
  return { depth: 1, expanded: false, hasChildren: false, node: node('loopring', 'blockchain', 'Loopring'), path: 'Blockchains › Loopring', ...overrides };
}

function createWrapper(value: LocationRow, search = ''): VueWrapper<InstanceType<typeof LocationTreeRowName>> {
  return mount(LocationTreeRowName, {
    global: { stubs: { LocationIcon: true } },
    props: { row: value, search },
  });
}

describe('locationTreeRowName', () => {
  it('should show the name as stored and mark the part a search matched', () => {
    const wrapper = createWrapper(row(), 'ING');
    expect(wrapper.find('[data-testid=location-row-name]').text()).toBe('Loopring');
    expect(wrapper.find('mark').text()).toBe('ing');
  });

  it('should offer a toggle only for a location with rows below it', async () => {
    expect(createWrapper(row()).find('[data-testid=location-toggle-children]').exists()).toBe(false);

    const wrapper = createWrapper(row({ expanded: true, hasChildren: true }));
    const toggle = wrapper.find('[data-testid=location-toggle-children]');
    expect(toggle.attributes('aria-expanded')).toBe('true');
    await toggle.trigger('click');
    expect(wrapper.emitted('toggle')).toHaveLength(1);
  });

  it('should tell custom and archived locations apart from the built-in ones', () => {
    expect(createWrapper(row()).text()).not.toContain('location_manager.custom');
    expect(createWrapper(row({ node: node('custom:ing', 'banks', 'ING', { isBuiltin: false }) })).text()).toContain('location_manager.custom');
    const archived = createWrapper(row({ node: node('custom:ing', 'banks', 'ING', { isActive: false, isBuiltin: false }) }));
    expect(archived.text()).toContain('location_manager.archived');
    expect(archived.text()).not.toContain('location_manager.custom');
  });
});
