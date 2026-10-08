import type { MenuNavItem } from '@/modules/shell/layout/use-navigation-menu';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import NavigationMenuLink from './NavigationMenuLink.vue';

/**
 * The seam is one thing: a drawer click must reach the router and nothing else.
 *
 * `RouterLink` is used in `custom` mode here, which leaves the anchor's default action in
 * place. Left unhandled, the click is a plain hash navigation racing the router's own, and
 * the entry the browser makes carries no state - which vue-router replaces with the position
 * it was already on, leaving two entries indistinguishable by position. Back from the second
 * then reads as a push and the overlay guard lets it through.
 */

vi.mock('vue-router', () => ({
  useRoute: (): { path: string } => ({ path: '/dashboard' }),
}));

const item: MenuNavItem = {
  icon: 'lu-coins',
  labelKey: 'navigation_menu.balances',
  path: '/balances/blockchain/',
  testId: 'balances-blockchain',
  type: 'item',
};

const navigate = vi.fn<(event: MouseEvent) => void>();

/** Hands the template the three slot props it reads off `RouterLink custom`. */
const routerLinkStub = defineComponent({
  props: {
    custom: { default: false, type: Boolean },
    to: { required: true, type: String },
  },
  setup(props, { slots }): () => unknown {
    return (): unknown => slots.default?.({ href: `#${props.to}`, isActive: false, navigate });
  },
});

function createWrapper(): VueWrapper<InstanceType<typeof NavigationMenuLink>> {
  return mount(NavigationMenuLink, {
    global: {
      stubs: {
        NavigationMenuItem: { template: '<div />' },
        RouterLink: routerLinkStub,
      },
    },
    props: { item },
  });
}

describe('modules/shell/components/navigation/NavigationMenuLink', () => {
  let wrapper: VueWrapper<InstanceType<typeof NavigationMenuLink>> | undefined;

  afterEach(() => {
    navigate.mockClear();
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should navigate through the router when the anchor is clicked', async () => {
    wrapper = createWrapper();

    await wrapper.get('a').trigger('click');

    expect(navigate).toHaveBeenCalledOnce();
  });

  it('should keep the href so the entry is still a real link', () => {
    wrapper = createWrapper();

    expect(wrapper.get('a').attributes('href')).toBe('#/balances/blockchain/');
  });
});
