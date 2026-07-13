import type { RuiIcons } from '@rotki/ui-library';
import type { RouteNamedMap } from 'vue-router/auto-routes';
import type { MessageKey } from '@/message-key';
import type { NoteLocation } from '@/modules/core/common/notes';

/**
 * Typed route name (a key of the generated route map). The router recommends `keyof RouteNamedMap`
 * over `RouteRecordName`, which resolves early to the generic (untyped) form.
 */
export type RouteName = keyof RouteNamedMap;

/**
 * Navigation metadata co-located with each route via `definePage({ meta: { nav } })`. It is the
 * single source for both the drawer and the global search palette, derived from `router.getRoutes()`
 * by `useNavigationMenu` and `useRouteSearch` respectively:
 *
 * - Search palette: every route with `nav` (the superset), unless `searchable` is false.
 * - Drawer: the subset whose `nav.drawer` is set. `parent`/`order`/`section` drive nesting and
 *   ordering; `parent` also supplies the search breadcrumb.
 */
export interface RouteNavMeta {
  /** i18n key for the label, resolved at render time (meta cannot hold reactive translations). */
  readonly labelKey: MessageKey;
  readonly icon: RuiIcons;
  /** Extra i18n keys matched by the search palette, for aliases beyond the label. */
  readonly keywords?: readonly MessageKey[];
  /** Route name of the logical parent: drawer nesting and the search breadcrumb both use it. */
  readonly parent?: string;
  /** Order among siblings (within the parent group, or within the drawer section). */
  readonly order?: number;
  /** Drawer top-level section; dividers separate sections. Sub-items omit it. */
  readonly section?: number;
  /** When set, the route shows in the drawer; the value is the `navigation__<id>` test selector. */
  readonly drawer?: string;
  /** Set false to exclude the route from the otherwise default-on search palette. */
  readonly searchable?: boolean;
  /**
   * Exposes a "quick add" action for this route in the search palette. Selecting it navigates to the
   * route with `?add=true` (which opens the page's add dialog). `labelKey` is the i18n key shown.
   */
  readonly addAction?: { readonly labelKey: MessageKey };
}

declare module 'vue-router' {
  interface RouteMeta {
    readonly title?: string;
    readonly noteLocation?: NoteLocation;
    readonly canNavigateBack?: boolean;
    readonly keepScrollPosition?: boolean;
    readonly nav?: RouteNavMeta;
  }
}
