import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';

export interface TabContent {
  readonly text: string;
  readonly icon: RuiIcons;
  readonly route: RouteLocationRaw;
}

/**
 * Derives a tab's `data-testid` from its resolved route path, so
 * `/settings/rpc` becomes `settings-rpc`.
 */
export function tabTestId(route: string): string {
  return route.toLowerCase().replace(/^\//, '').replace(/\//g, '-');
}
