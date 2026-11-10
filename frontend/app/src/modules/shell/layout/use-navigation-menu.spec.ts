import type { RouteNavMeta } from '@/types/router';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { msg } from '@/message-key';
import { type MenuItem, type MenuNavGroup, type MenuNavItem, useNavigationMenu } from '@/modules/shell/layout/use-navigation-menu';

interface FakeRoute {
  name: string;
  meta: { nav?: RouteNavMeta };
}

const routes = ref<FakeRoute[]>([]);

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    getRoutes: (): FakeRoute[] => get(routes),
    hasRoute: (name: string): boolean => get(routes).some(route => route.name === name),
    // The resolved path mirrors the route name in these tests, which is enough for the derivation.
    resolve: ({ name }: { name: string }): { path: string } => ({ path: name }),
  })),
}));

type FakeNav = Omit<RouteNavMeta, 'icon' | 'labelKey' | 'drawerLabelKey' | 'heading'> & {
  labelKey: string;
  drawerLabelKey?: string;
  heading?: string;
};

function route(name: string, nav?: FakeNav): FakeRoute {
  if (!nav)
    return { name, meta: {} };
  const { drawerLabelKey, heading, labelKey, ...rest } = nav;
  return {
    name,
    meta: {
      nav: {
        icon: 'lu-wallet',
        ...rest,
        labelKey: msg.$t(labelKey),
        ...(drawerLabelKey ? { drawerLabelKey: msg.$t(drawerLabelKey) } : {}),
        ...(heading ? { heading: msg.$t(heading) } : {}),
      },
    },
  };
}

function itemAt(items: MenuItem[], index: number): MenuNavItem {
  const item = items[index];
  assert(item?.type === 'item', `expected an item at index ${index}`);
  return item;
}

function groupAt(items: MenuItem[], index: number): MenuNavGroup {
  const item = items[index];
  assert(item?.type === 'group', `expected a group at index ${index}`);
  return item;
}

describe('modules::shell::use-navigation-menu', () => {
  beforeEach(() => {
    set(routes, []);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should ignore routes without a drawer flag', () => {
    set(routes, [
      route('/dashboard/', { labelKey: 'dashboard', order: 10, section: 1, drawer: 'dashboard' }),
      // has nav (searchable) but no drawer flag -> not in the drawer
      route('/settings/account/', { labelKey: 'account', parent: '/settings' }),
      route('/hidden/'),
    ]);

    const { menuItems } = useNavigationMenu();

    expect(get(menuItems)).toHaveLength(1);
    expect(itemAt(get(menuItems), 0).path).toBe('/dashboard/');
  });

  it('should order top-level entries by section then order', () => {
    set(routes, [
      route('/nfts/', { labelKey: 'nfts', order: 90, section: 1, drawer: 'nfts' }),
      route('/dashboard/', { labelKey: 'dashboard', order: 10, section: 1, drawer: 'dashboard' }),
    ]);

    const { menuItems } = useNavigationMenu();

    expect(get(menuItems).map((item) => {
      assert(item.type === 'item');
      return item.testId;
    })).toStrictEqual(['dashboard', 'nfts']);
  });

  it('should insert a divider between sections', () => {
    set(routes, [
      route('/dashboard/', { labelKey: 'dashboard', order: 10, section: 1, drawer: 'dashboard' }),
      route('/tag-manager/', { labelKey: 'tags', order: 10, section: 2, drawer: 'tag-manager' }),
    ]);

    const { menuItems } = useNavigationMenu();

    expect(get(menuItems).map(item => item.type)).toStrictEqual(['item', 'divider', 'item']);
  });

  it('should group children under their parent, ordered by order, children without one first', () => {
    set(routes, [
      route('/balances/', { labelKey: 'balances', order: 30, section: 1, drawer: 'balances' }),
      route('/balances/nft/', { labelKey: 'nft', parent: '/balances/', drawer: 'balances-nft' }),
      route('/balances/exchange/', { labelKey: 'exchange', order: 20, parent: '/balances/', drawer: 'balances-exchange' }),
      route('/balances/blockchain/', { labelKey: 'blockchain', order: 10, parent: '/balances/', drawer: 'balances-blockchain' }),
      route('/balances/manual/', { labelKey: 'manual', parent: '/balances/', drawer: 'balances-manual' }),
    ]);

    const { menuItems } = useNavigationMenu();
    const group = groupAt(get(menuItems), 0);

    expect(group.testId).toBe('balances');
    expect(group.items.map(item => item.testId)).toStrictEqual(['balances-nft', 'balances-manual', 'balances-blockchain', 'balances-exchange']);
  });

  it('should mark the first child of each heading run with its heading', () => {
    set(routes, [
      route('/accounts/', { labelKey: 'accounts', order: 20, section: 1, drawer: 'accounts' }),
      route('/accounts/banks/', { labelKey: 'banks', order: 40, parent: '/accounts/', heading: 'fiat', drawer: 'accounts-banks' }),
      route('/accounts/bitcoin/', { labelKey: 'bitcoin', order: 20, parent: '/accounts/', heading: 'chains', drawer: 'accounts-bitcoin' }),
      route('/accounts/evm/', { labelKey: 'evm', order: 10, parent: '/accounts/', heading: 'chains', drawer: 'accounts-evm' }),
      route('/accounts/exchanges/', { labelKey: 'exchanges', order: 30, parent: '/accounts/', heading: 'fiat', drawer: 'accounts-exchanges' }),
    ]);

    const { menuItems } = useNavigationMenu();
    const group = groupAt(get(menuItems), 0);

    expect(group.items.map(item => [item.testId, item.headingKey])).toStrictEqual([
      ['accounts-evm', 'chains'],
      ['accounts-bitcoin', undefined],
      ['accounts-exchanges', 'fiat'],
      ['accounts-banks', undefined],
    ]);
  });

  it('should leave children without a heading unmarked', () => {
    set(routes, [
      route('/balances/', { labelKey: 'balances', order: 30, section: 1, drawer: 'balances' }),
      route('/balances/blockchain/', { labelKey: 'blockchain', order: 10, parent: '/balances/', drawer: 'balances-blockchain' }),
    ]);

    const { menuItems } = useNavigationMenu();

    expect(groupAt(get(menuItems), 0).items[0]?.headingKey).toBeUndefined();
  });

  it('should label a drawer entry with its drawer label when it has one', () => {
    set(routes, [
      route('/accounts/', { labelKey: 'accounts', order: 20, section: 1, drawer: 'accounts' }),
      route('/accounts/evm/', { labelKey: 'evm-accounts', drawerLabelKey: 'evm', order: 10, parent: '/accounts/', drawer: 'accounts-evm' }),
      route('/accounts/banks/', { labelKey: 'banks', order: 20, parent: '/accounts/', drawer: 'accounts-banks' }),
    ]);

    const { menuItems } = useNavigationMenu();

    expect(groupAt(get(menuItems), 0).items.map(item => item.labelKey)).toStrictEqual(['evm', 'banks']);
  });

  describe('history / data-issues gate', () => {
    function historyRoutes(): FakeRoute[] {
      return [
        route('/history/', { labelKey: 'history', order: 40, section: 1, drawer: 'history' }),
        route('/history/events/', { labelKey: 'events', order: 10, parent: '/history/', drawer: 'history-events' }),
        route('/history/data-issues/[[tab]]', { labelKey: 'data-issues', order: 20, parent: '/history/', drawer: 'history-data-issues' }),
      ];
    }

    it('should render history as a group with both children when enabled', () => {
      vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
      set(routes, historyRoutes());

      const { menuItems } = useNavigationMenu();
      const group = groupAt(get(menuItems), 0);

      expect(group.items.map(item => item.testId)).toStrictEqual(['history-events', 'history-data-issues']);
    });

    it('should collapse history to an item linking to events when disabled', () => {
      vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
      set(routes, historyRoutes());

      const { menuItems } = useNavigationMenu();
      const item = itemAt(get(menuItems), 0);

      expect(item.testId).toBe('history');
      expect(item.path).toBe('/history/events/');
      expect(get(menuItems)).toHaveLength(1);
    });
  });
});
