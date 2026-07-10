import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { RouteRecordNameGeneric } from 'vue-router';
import type { TabContent } from '@/modules/core/common/tabs';
import type { RouteName, RouteNavMeta } from '@/types/router';

function tabContent(router: ReturnType<typeof useRouter>, t: ReturnType<typeof useI18n>['t'], name: RouteName, labelKey: string, icon: TabContent['icon']): TabContent {
  return {
    route: router.resolve({ name }).path,
    text: t(labelKey),
    icon,
  };
}

/**
 * Builds a `TabContent[]` (route, label, icon) for the given child routes straight from their
 * `nav` meta, so tab bars for sub-page grids need no separate route/label list to maintain. Use this
 * when the tab set is a specific subset or needs an explicit order; prefer `useChildNavTabs` when the
 * bar is simply every child of a parent.
 */
export function useNavTabs(names: MaybeRefOrGetter<RouteName[]>): ComputedRef<TabContent[]> {
  const router = useRouter();
  const { t } = useI18n({ useScope: 'global' });

  // A name without nav meta is skipped rather than throwing, so one misconfigured route cannot break
  // the whole tab bar.
  return computed<TabContent[]>(() => toValue(names)
    .map((name) => {
      const nav = router.getRoutes().find(route => route.name === name)?.meta.nav;
      return nav ? tabContent(router, t, name, nav.labelKey, nav.icon) : undefined;
    })
    .filter((tab): tab is TabContent => tab !== undefined));
}

/**
 * Builds a `TabContent[]` for every route whose `nav.parent` is `parentName`, ordered by `nav.order`.
 * The tab bar then tracks the routes automatically: adding a child page adds its tab.
 */
export function useChildNavTabs(parentName: RouteName): ComputedRef<TabContent[]> {
  const router = useRouter();
  const { t } = useI18n({ useScope: 'global' });
  const isRouteName = (name: RouteRecordNameGeneric): name is RouteName => name !== undefined && router.hasRoute(name);

  return computed<TabContent[]>(() => {
    const children: { name: RouteName; nav: RouteNavMeta }[] = [];
    for (const route of router.getRoutes()) {
      const nav = route.meta.nav;
      if (nav?.parent === parentName && isRouteName(route.name))
        children.push({ name: route.name, nav });
    }

    return children
      .sort((a, b) => (a.nav.order ?? 0) - (b.nav.order ?? 0))
      .map(({ name, nav }) => tabContent(router, t, name, nav.labelKey, nav.icon));
  });
}
