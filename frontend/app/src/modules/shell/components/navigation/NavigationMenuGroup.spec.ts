import type { MenuNavGroup } from '@/modules/shell/layout/use-navigation-menu';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import NavigationMenuGroup from './NavigationMenuGroup.vue';

const group: MenuNavGroup = {
  icon: 'lu-wallet',
  items: [
    { headingKey: 'navigation_menu.accounts_sub.heading.blockchain', labelKey: 'evm', path: '/accounts/evm/', testId: 'accounts-evm', type: 'item' },
    { labelKey: 'bitcoin', path: '/accounts/bitcoin/', testId: 'accounts-bitcoin', type: 'item' },
    { headingKey: 'navigation_menu.accounts_sub.heading.exchanges_and_banks', labelKey: 'banks', path: '/accounts/banks/', testId: 'accounts-banks', type: 'item' },
  ],
  labelKey: 'navigation_menu.accounts',
  path: '/accounts/',
  testId: 'accounts',
  type: 'group',
};

const routerLinkStub = defineComponent({
  props: {
    custom: { default: false, type: Boolean },
    to: { required: true, type: String },
  },
  setup(_props, { slots }): () => unknown {
    return (): unknown => slots.default?.({ isActive: false });
  },
});

function createWrapper(mini: boolean): VueWrapper<InstanceType<typeof NavigationMenuGroup>> {
  return mount(NavigationMenuGroup, {
    global: {
      stubs: {
        NavigationMenuItem: { template: '<div><slot /></div>' },
        NavigationMenuLink: { props: ['item'], template: '<div data-testid="link" :data-key="item.testId" />' },
        RouterLink: routerLinkStub,
      },
    },
    props: { group, mini },
  });
}

describe('modules/shell/components/navigation/NavigationMenuGroup', () => {
  it('should show each heading once, above the first child of its run', () => {
    const wrapper = createWrapper(false);

    const sequence = wrapper.findAll('[data-testid="navigation-heading"], [data-testid="link"]')
      .map(node => node.attributes('data-key') ?? node.text());

    expect(sequence).toStrictEqual([
      'navigation_menu.accounts_sub.heading.blockchain',
      'accounts-evm',
      'accounts-bitcoin',
      'navigation_menu.accounts_sub.heading.exchanges_and_banks',
      'accounts-banks',
    ]);
  });

  it('should replace headings with a divider between runs when mini', () => {
    const wrapper = createWrapper(true);

    expect(wrapper.find('[data-testid="navigation-heading"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="navigation-heading-divider"]')).toHaveLength(1);
  });
});
