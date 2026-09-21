import type { RuiIcons } from '@rotki/ui-library';

/**
 * The icons a custom location can use.
 *
 * @remarks
 * The app only registers icons whose names appear in its source, so a user can only pick from a
 * list spelled out here. An icon the backend holds that is not in the list shows the default.
 */
export const LOCATION_ICONS = [
  'lu-map-pin',
  'lu-landmark',
  'lu-building-2',
  'lu-vault',
  'lu-piggy-bank',
  'lu-wallet',
  'lu-credit-card',
  'lu-banknote',
  'lu-coins',
  'lu-hand-coins',
  'lu-chart-line',
  'lu-briefcase',
  'lu-store',
  'lu-house',
  'lu-globe',
  'lu-gem',
  'lu-server',
  'lu-layers',
  'lu-link',
  'lu-archive',
] as const satisfies readonly RuiIcons[];

export type LocationIcon = typeof LOCATION_ICONS[number];

export const DEFAULT_LOCATION_ICON: LocationIcon = 'lu-map-pin';

const LOCATION_ICON_SET: ReadonlySet<string> = new Set(LOCATION_ICONS);

export function isLocationIcon(icon: string | null): icon is LocationIcon {
  return icon !== null && LOCATION_ICON_SET.has(icon);
}
