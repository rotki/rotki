import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';

const { collapsed } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { collapsed: ref<boolean>(false) };
});

vi.mock('@/modules/core/table/table-selection-collapse', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/table-selection-collapse')>(),
  useSelectionBarCollapse: (): typeof collapsed => collapsed,
}));

const stubs = {
  RuiMenu: { template: '<div data-testid="menu"><slot name="activator" :attrs="{}" /><slot /></div>' },
};

function createWrapper(): VueWrapper {
  return mount({
    components: { TableSelectionAction, TableSelectionBar },
    template: `
      <TableSelectionBar :count="2" exitable>
        <TableSelectionAction icon="lu-eye-off" data-testid="ignore">Ignore</TableSelectionAction>
      </TableSelectionBar>`,
  }, { global: { provide: libraryDefaults, stubs } });
}

describe('modules/core/table/TableSelectionBar', () => {
  beforeEach(() => {
    set(collapsed, false);
  });

  it('should lay the actions out in the bar while they fit', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid="menu"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="table-selection-actions"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="ignore"]').exists()).toBe(true);
  });

  it('should move the actions into a menu, rendered as menu entries, once the bar is too narrow', async () => {
    const wrapper = createWrapper();
    set(collapsed, true);
    await nextTick();

    const menu = wrapper.find('[data-testid="menu"]');
    expect(menu.find('[data-testid="table-selection-actions"]').exists()).toBe(true);
    expect(menu.find('[data-testid="ignore"]').exists()).toBe(true);
    expect(wrapper.findComponent(TableSelectionAction).findComponent({ name: 'RuiButton' }).props('variant')).toBe('list');
  });

  it('should keep the count, clear and done outside the menu when collapsed', async () => {
    const wrapper = createWrapper();
    set(collapsed, true);
    await nextTick();

    const menu = wrapper.find('[data-testid="menu"]');
    expect(menu.find('[data-testid="table-selection-count"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="table-selection-count"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="table-selection-clear"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="table-selection-exit"]').exists()).toBe(true);
  });
});
