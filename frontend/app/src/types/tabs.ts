import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';

export interface TabContent {
  readonly text: string;
  readonly icon: RuiIcons;
  readonly route: RouteLocationRaw;
}

export function getClass(route: string): string {
  return route.toLowerCase().replace('/', '').replace(/\//g, '__');
}
