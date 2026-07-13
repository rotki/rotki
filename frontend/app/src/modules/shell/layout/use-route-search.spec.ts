import type { RouteNavMeta } from '@/types/router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { msg } from '@/message-key';
import { useRouteSearch } from '@/modules/shell/layout/use-route-search';

interface FakeRoute {
  name: string;
  meta: { nav?: RouteNavMeta };
}

const routes = ref<FakeRoute[]>([]);

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    getRoutes: (): FakeRoute[] => get(routes),
    hasRoute: (name: string): boolean => get(routes).some(route => route.name === name),
    resolve: ({ name }: { name: string }): { path: string } => ({ path: name }),
  })),
}));

function route(name: string, nav?: Omit<RouteNavMeta, 'icon' | 'labelKey'> & { labelKey: string }): FakeRoute {
  return { name, meta: nav ? { nav: { icon: 'lu-wallet', ...nav, labelKey: msg.$t(nav.labelKey) } } : {} };
}

describe('modules::shell::use-route-search', () => {
  beforeEach(() => {
    set(routes, []);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should include every nav route and resolve the breadcrumb from the parent label', () => {
    set(routes, [
      route('/accounts/', { labelKey: 'navigation_menu.accounts' }),
      route('/accounts/evm/', { labelKey: 'evm', parent: '/accounts/' }),
      route('/hidden/'),
    ]);

    const { searchEntries } = useRouteSearch();
    const entries = get(searchEntries);

    expect(entries).toHaveLength(2);
    const evm = entries.find(entry => entry.labelKey === 'evm');
    expect(evm?.parentLabelKey).toBe('navigation_menu.accounts');
    expect(evm?.path).toBe('/accounts/evm/');
  });

  it('should exclude routes with searchable: false', () => {
    set(routes, [
      route('/dashboard/', { labelKey: 'dashboard' }),
      route('/settings', { labelKey: 'settings', searchable: false }),
    ]);

    const { searchEntries } = useRouteSearch();

    expect(get(searchEntries).map(entry => entry.labelKey)).toStrictEqual(['dashboard']);
  });

  it('should hide data-issues from search when the accounting update is disabled', () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
    set(routes, [
      route('/history/events/', { labelKey: 'events', parent: '/history/' }),
      route('/history/data-issues/', { labelKey: 'data-issues', parent: '/history/' }),
    ]);

    const { searchEntries } = useRouteSearch();

    expect(get(searchEntries).map(entry => entry.labelKey)).toStrictEqual(['events']);
  });

  it('should include data-issues in search when the accounting update is enabled', () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    set(routes, [
      route('/history/events/', { labelKey: 'events', parent: '/history/' }),
      route('/history/data-issues/', { labelKey: 'data-issues', parent: '/history/' }),
    ]);

    const { searchEntries } = useRouteSearch();

    expect(get(searchEntries).map(entry => entry.labelKey)).toContain('data-issues');
  });
});
