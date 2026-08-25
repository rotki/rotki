import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';

export interface TabContent {
  readonly text: string;
  readonly icon: RuiIcons;
  readonly route: RouteLocationRaw;
}

/**
 * Derives a tab's `data-key` from its resolved route path.
 *
 * @param route - a resolved route path, e.g. `/settings/rpc`
 * @returns the key, e.g. `settings-rpc`
 */
export function tabKey(route: string): string {
  return route.toLowerCase().replace(/^\//, '').replace(/\//g, '-');
}
