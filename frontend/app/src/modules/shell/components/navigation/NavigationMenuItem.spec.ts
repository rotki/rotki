import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import NavigationMenuItem from '@/modules/shell/components/navigation/NavigationMenuItem.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock('vue-router', () => ({
  useRouter: (): { push: Mock } => ({ push }),
}));

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(NavigationMenuItem, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { AppImage: true },
    },
    props: { text: 'Balances', ...props },
    slots: { default: '<div data-testid="child">child</div>' },
  });
}

function isExpanded(wrapper: VueWrapper<any>): boolean {
  return wrapper.find('[data-testid=submenu-wrapper]').attributes('data-expanded') === 'true';
}

describe('navigationMenuItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /** A leaf is a plain link handled by the router-link around it; only a parent expands. */
  describe('a leaf item', () => {
    it('should carry no submenu at all', () => {
      expect(createWrapper().find('[data-testid=submenu-wrapper]').exists()).toBe(false);
    });

    it('should not navigate on its own', async () => {
      const wrapper = createWrapper({ to: '/balances' });

      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');

      expect(push).not.toHaveBeenCalled();
    });
  });

  describe('a parent item', () => {
    it('should start collapsed', () => {
      expect(isExpanded(createWrapper({ parent: true }))).toBe(false);
    });

    /** Landing on a page inside the group should show the user where they are. */
    it('should start expanded when the group holds the active page', async () => {
      const wrapper = createWrapper({ active: true, parent: true });
      await nextTick();

      expect(isExpanded(wrapper)).toBe(true);
    });

    it('should not start expanded when only active and not a parent', () => {
      expect(createWrapper({ active: true }).find('[data-testid=submenu-wrapper]').exists()).toBe(false);
    });

    it('should expand when its body is pressed', async () => {
      const wrapper = createWrapper({ parent: true });

      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');

      expect(isExpanded(wrapper)).toBe(true);
    });

    it('should collapse again when pressed a second time', async () => {
      const wrapper = createWrapper({ parent: true });

      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');
      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');

      expect(isExpanded(wrapper)).toBe(false);
    });

    /**
     * A parent that is itself a page opens that page as it expands, so pressing it once both shows
     * the group and goes where the user asked.
     */
    it('should open its own page as it expands', async () => {
      const wrapper = createWrapper({ parent: true, to: '/balances' });

      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');

      expect(push).toHaveBeenCalledWith('/balances');
      expect(isExpanded(wrapper)).toBe(true);
    });

    /** Collapsing is not a navigation, so pressing an open group only closes it. */
    it('should not navigate again when collapsing', async () => {
      const wrapper = createWrapper({ parent: true, to: '/balances' });
      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');
      push.mockClear();

      await wrapper.find('[data-testid=navigation-item-body]').trigger('click');

      expect(push).not.toHaveBeenCalled();
      expect(isExpanded(wrapper)).toBe(false);
    });

    it('should expand from the chevron without navigating', async () => {
      const wrapper = createWrapper({ parent: true, to: '/balances' });

      await wrapper.find('[data-testid=navigation-item-chevron]').trigger('click');

      expect(isExpanded(wrapper)).toBe(true);
      expect(push).not.toHaveBeenCalled();
    });

    /** The collapsed rail has no room for a chevron, and nothing to expand into. */
    it('should offer no chevron while the menu is collapsed to icons', () => {
      const wrapper = createWrapper({ mini: true, parent: true });

      expect(wrapper.find('[data-testid=navigation-item-chevron]').exists()).toBe(false);
    });
  });
});
