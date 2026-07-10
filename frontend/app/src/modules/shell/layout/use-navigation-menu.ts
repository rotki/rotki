import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import type { RouteRecordNameGeneric } from 'vue-router';
import type { RouteName, RouteNavMeta } from '@/types/router';

interface MenuEntry {
  readonly name: RouteName;
  readonly nav: RouteNavMeta;
}

export interface MenuNavItem {
  readonly type: 'item';
  /** Resolved path used for `<RouterLink :to>` and active-state matching. */
  readonly path: string;
  readonly labelKey: string;
  readonly icon?: RuiIcons;
  readonly testId: string;
}

export interface MenuNavGroup {
  readonly type: 'group';
  readonly path: string;
  readonly labelKey: string;
  readonly icon?: RuiIcons;
  readonly testId: string;
  readonly items: MenuNavItem[];
}

export interface MenuDivider {
  readonly type: 'divider';
}

export type MenuItem = MenuNavItem | MenuNavGroup | MenuDivider;

// The data-issues inbox is part of the accounting refactor and only served in builds where the
// backend exposes it (ROTKI_ACCOUNTING_UPDATE, mirrored into VITE_ACCOUNTING_UPDATE in
// vite.config.ts). When disabled, History collapses from a group into a single item that links
// straight to Events.
const HISTORY_ROUTE = '/history/';
const HISTORY_EVENTS_ROUTE = '/history/events/';
const HISTORY_DATA_ISSUES_ROUTE = '/history/data-issues/';

interface UseNavigationMenuReturn {
  menuItems: ComputedRef<MenuItem[]>;
}

/**
 * Derives the drawer navigation entirely from the router. Every drawer entry is declared next to its
 * page via `definePage({ meta: { nav } })` with `nav.drawer` set; this composable reads
 * `router.getRoutes()`, groups the entries by `parent`, orders them by `section`/`order`, and inserts
 * dividers between sections.
 */
export function useNavigationMenu(): UseNavigationMenuReturn {
  const router = useRouter();
  const dataIssuesEnabled = !!import.meta.env.VITE_ACCOUNTING_UPDATE;

  // A name taken from the live router is always registered, so `hasRoute` both validates it and
  // narrows the generic route name to a typed RouteName. This is the type-safe alternative to a cast.
  const isRouteName = (name: RouteRecordNameGeneric): name is RouteName =>
    name !== undefined && router.hasRoute(name);

  const pathOf = (name: RouteName): string => router.resolve({ name }).path;

  const sectionOf = (entry: MenuEntry): number => entry.nav.section ?? 0;

  const toItem = (entry: MenuEntry): MenuNavItem => ({
    type: 'item',
    path: pathOf(entry.name),
    labelKey: entry.nav.labelKey,
    icon: entry.nav.icon,
    testId: entry.nav.drawer ?? '',
  });

  // Splits the drawer routes into ordered top-level entries and a parent -> children lookup.
  function collectEntries(): { topLevel: MenuEntry[]; childrenByParent: Map<string, MenuEntry[]> } {
    const childrenByParent = new Map<string, MenuEntry[]>();
    const topLevel: MenuEntry[] = [];

    for (const route of router.getRoutes()) {
      const nav = route.meta.nav;
      if (!nav || nav.drawer === undefined || !isRouteName(route.name))
        continue;
      if (route.name === HISTORY_DATA_ISSUES_ROUTE && !dataIssuesEnabled)
        continue;

      const entry: MenuEntry = { name: route.name, nav };
      const siblings = nav.parent ? (childrenByParent.get(nav.parent) ?? []) : topLevel;
      siblings.push(entry);
      if (nav.parent)
        childrenByParent.set(nav.parent, siblings);
    }

    topLevel.sort((a, b) => sectionOf(a) - sectionOf(b) || (a.nav.order ?? 0) - (b.nav.order ?? 0));
    return { topLevel, childrenByParent };
  }

  // Turns a top-level entry into a group (when it has children) or a plain item, collapsing History
  // to an Events link when the data-issues inbox is disabled.
  function toEntry(entry: MenuEntry, children: MenuEntry[]): MenuNavItem | MenuNavGroup {
    if (entry.name === HISTORY_ROUTE && !dataIssuesEnabled)
      return { ...toItem(entry), path: pathOf(HISTORY_EVENTS_ROUTE) };

    if (children.length === 0)
      return toItem(entry);

    const items = [...children].sort((a, b) => (a.nav.order ?? 0) - (b.nav.order ?? 0)).map(toItem);
    return { ...toItem(entry), type: 'group', items };
  }

  const menuItems = computed<MenuItem[]>(() => {
    const { topLevel, childrenByParent } = collectEntries();
    const result: MenuItem[] = [];
    let previousSection: number | undefined;

    for (const entry of topLevel) {
      if (previousSection !== undefined && sectionOf(entry) !== previousSection)
        result.push({ type: 'divider' });
      previousSection = sectionOf(entry);
      result.push(toEntry(entry, childrenByParent.get(entry.name) ?? []));
    }

    return result;
  });

  return { menuItems };
}
