import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import type { RouteRecordNameGeneric } from 'vue-router';
import type { RouteName } from '@/types/router';

export interface RouteSearchEntry {
  /** Resolved path used as the navigation target. */
  readonly path: string;
  readonly icon?: RuiIcons;
  /** i18n key of the entry label. */
  readonly labelKey: string;
  /** i18n key of the parent label, shown as a breadcrumb ahead of the label. */
  readonly parentLabelKey?: string;
  /** Extra i18n keys the entry can be matched by. */
  readonly keywordKeys: readonly string[];
}

export interface RouteActionEntry {
  /** Resolved path (with `?add=true`) that opens the route's add dialog. */
  readonly path: string;
  /** i18n key of the action label. */
  readonly labelKey: string;
}

interface UseRouteSearchReturn {
  searchEntries: ComputedRef<RouteSearchEntry[]>;
  actionEntries: ComputedRef<RouteActionEntry[]>;
}

/**
 * Derives the global-search palette from the router. Every route declaring `meta.nav` is searchable
 * (the superset of the drawer) unless it opts out with `searchable: false`; the breadcrumb is the
 * label of the route named by `nav.parent`.
 */
// Kept in sync with the drawer gate in `useNavigationMenu`: the data-issues inbox only exists in
// builds where VITE_ACCOUNTING_UPDATE is set, so it must be hidden from search there too.
const HISTORY_DATA_ISSUES_ROUTE = '/history/data-issues/';

export function useRouteSearch(): UseRouteSearchReturn {
  const router = useRouter();
  const dataIssuesEnabled = !!import.meta.env.VITE_ACCOUNTING_UPDATE;

  const isRouteName = (name: RouteRecordNameGeneric): name is RouteName =>
    name !== undefined && router.hasRoute(name);

  const searchEntries = computed<RouteSearchEntry[]>(() => {
    const routes = router.getRoutes();
    // Resolve breadcrumb labels: nav.parent is a route name; look up its label.
    const labelByName = new Map<string, string>();
    for (const route of routes) {
      if (route.meta.nav && isRouteName(route.name))
        labelByName.set(route.name, route.meta.nav.labelKey);
    }

    const entries: RouteSearchEntry[] = [];
    for (const route of routes) {
      const nav = route.meta.nav;
      if (!nav || nav.searchable === false || !isRouteName(route.name))
        continue;
      if (route.name === HISTORY_DATA_ISSUES_ROUTE && !dataIssuesEnabled)
        continue;

      entries.push({
        path: router.resolve({ name: route.name }).path,
        icon: nav.icon,
        labelKey: nav.labelKey,
        parentLabelKey: nav.parent ? labelByName.get(nav.parent) : undefined,
        keywordKeys: nav.keywords ?? [],
      });
    }

    return entries;
  });

  // "Quick add" actions: any route declaring nav.addAction, targeting the route with ?add=true.
  const actionEntries = computed<RouteActionEntry[]>(() => {
    const entries: RouteActionEntry[] = [];
    for (const route of router.getRoutes()) {
      const addAction = route.meta.nav?.addAction;
      if (!addAction || !isRouteName(route.name))
        continue;

      entries.push({
        path: router.resolve({ name: route.name, query: { add: 'true' } }).fullPath,
        labelKey: addAction.labelKey,
      });
    }
    return entries;
  });

  return { searchEntries, actionEntries };
}
