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

const QUESTION = { confirmLabel: 'Delete', message: 'Delete 2 backups?', title: 'Delete backups' };

function createAskingWrapper(onClick: () => void): VueWrapper {
  return mount({
    components: { TableSelectionAction, TableSelectionBar },
    setup: () => ({ onClick, question: QUESTION }),
    template: `
      <TableSelectionBar :count="2">
        <TableSelectionAction icon="lu-trash-2" :confirm="question" data-testid="delete" @click="onClick()">Delete</TableSelectionAction>
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

  describe('an action that asks first, once collapsed', () => {
    async function openQuestion(onClick: () => void): Promise<VueWrapper> {
      const wrapper = createAskingWrapper(onClick);
      set(collapsed, true);
      await nextTick();
      await wrapper.find('[data-testid="delete"]').trigger('click');
      return wrapper;
    }

    it('should ask in the menu in place of the entries, keeping the menu open, without acting', async () => {
      const onClick = vi.fn<() => void>();
      const wrapper = await openQuestion(onClick);

      const menu = wrapper.findComponent(stubs.RuiMenu);
      expect(menu.find('[data-testid="table-selection-confirm"]').text()).toContain('Delete 2 backups?');
      expect(menu.find('[data-testid="table-selection-entries"]').attributes('style')).toContain('display: none');
      expect(menu.attributes('close-on-content-click')).toBe('false');
      expect(onClick).not.toHaveBeenCalled();
    });

    it('should act once the question is accepted', async () => {
      const onClick = vi.fn<() => void>();
      const wrapper = await openQuestion(onClick);

      await wrapper.find('[data-testid="inline-confirm-accept"]').trigger('click');

      expect(onClick).toHaveBeenCalledOnce();
      expect(wrapper.find('[data-testid="table-selection-confirm"]').exists()).toBe(false);
    });

    it('should bring the entries back on cancel, without acting', async () => {
      const onClick = vi.fn<() => void>();
      const wrapper = await openQuestion(onClick);

      await wrapper.find('[data-testid="inline-confirm-cancel"]').trigger('click');

      expect(onClick).not.toHaveBeenCalled();
      expect(wrapper.find('[data-testid="table-selection-entries"]').attributes('style') ?? '').not.toContain('display: none');
      expect(wrapper.find('[data-testid="table-selection-confirm"]').exists()).toBe(false);
    });
  });

  it('should ask beside the action, and only act once accepted, while the bar is wide', async () => {
    const onClick = vi.fn<() => void>();
    const wrapper = createAskingWrapper(onClick);

    expect(onClick).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid="inline-confirm"]').text()).toContain('Delete 2 backups?');

    await wrapper.find('[data-testid="inline-confirm-accept"]').trigger('click');

    expect(onClick).toHaveBeenCalledOnce();
  });
});
