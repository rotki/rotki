import type { RuiIcons } from '@rotki/ui-library';

export interface TabContent {
  readonly text: string;
  readonly icon: RuiIcons;
  readonly route: string;
}

export function getClass(route: string): string {
  return route.toLowerCase().replace('/', '').replace(/\//g, '__');
}
