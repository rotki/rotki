import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import { NON_TERMINAL_STATES } from '@/modules/history/data-issues/constants';
import { DataIssuesFilterKeys, type Filters } from '@/modules/history/data-issues/use-data-issues-filter';

/**
 * The panel is a glanceable inbox preview: it loads one page at a time and appends
 * more as the user scrolls, rather than mounting the entire (possibly 100+) list at
 * once (each card resolves an asset icon/avatar and runs observers).
 */
export const PANEL_PAGE_SIZE = 25;

/**
 * The compact filter subset that fits the preview, keyed by wire key (which is what
 * a field carries). The period pill is left out because the preview is a glance at
 * what needs attention now, not a search.
 */
export const PANEL_FILTER_KEYS: readonly string[] = [
  DataIssuesFilterKeys.STATE,
  DataIssuesFilterKeys.KIND,
  DataIssuesFilterKeys.ASSET,
  DataIssuesFilterKeys.ACCOUNT,
];

/** Reuses the full-page filter fields, but exposes only the subset above. */
export function panelFilterFields(fields: FieldDef[]): FieldDef[] {
  return fields.filter(field => PANEL_FILTER_KEYS.includes(field.key));
}

// Filter values are typed `string | string[] | boolean`; these fields only ever
// produce strings/arrays, so narrow to the shapes the request payload accepts.
type FilterValue = string | string[] | boolean | undefined;

export function asMulti(value: FilterValue): string | string[] | undefined {
  return value === undefined || typeof value === 'boolean' ? undefined : value;
}

export function asSingle(value: FilterValue): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

/**
 * Builds the list request for a page of the panel. With no state filter engaged the
 * panel falls back to the non-terminal states, so a resolved or dismissed issue never
 * appears in the preview.
 */
export function buildPanelPayload(filters: Filters, offset: number): DataIssuesRequestPayload {
  return {
    asset: asSingle(filters.asset),
    kind: asMulti(filters.kind),
    limit: PANEL_PAGE_SIZE,
    locationLabel: asSingle(filters.locationLabel),
    offset,
    state: asMulti(filters.state) ?? [...NON_TERMINAL_STATES],
  };
}
