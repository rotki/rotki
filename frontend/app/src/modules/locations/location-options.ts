import type { TradeLocationData } from '@/modules/core/common/location';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';

export interface LocationOption {
  readonly identifier: string;
  readonly name: string;
  /** The names from below the total down to the location, e.g. `Banks › ING`, which search matches. */
  readonly label: string;
  /** The names of the location's ancestors below the total, empty for a top level location. */
  readonly parentPath: string;
}

export interface LocationOptionsInput {
  /** Every location with display data: built-in and custom. */
  readonly locations: readonly TradeLocationData[];
  /** The locations new data can go to, or undefined while the tree has not loaded. */
  readonly assignable: ReadonlySet<string> | undefined;
  readonly pathOf: (identifier: string) => LocationNode[];
  /** Restricts the options to these locations, whatever their state. */
  readonly items: readonly string[];
  readonly excludes: readonly string[];
  /** The current value, offered even if new data can no longer go there. */
  readonly current: string;
}

const PATH_SEPARATOR = ' › ';

/**
 * The options of a location selector.
 *
 * @remarks
 * Without explicit items it offers the locations new data can be assigned to, so the total and
 * archived locations are left out, but the current value stays so that an old record still shows
 * where it is. Explicit items are offered as given, since a caller listing them knows they apply.
 */
export function locationOptions({ assignable, current, excludes, items, locations, pathOf }: LocationOptionsInput): LocationOption[] {
  const wanted = (identifier: string): boolean => {
    if (excludes.includes(identifier))
      return false;
    if (items.length > 0)
      return items.includes(identifier);
    return assignable === undefined || assignable.has(identifier) || identifier === current;
  };

  return locations.filter(location => wanted(location.identifier)).map((location) => {
    const path = pathOf(location.identifier);
    const parentPath = path.slice(0, -1).map(node => node.name).join(PATH_SEPARATOR);
    return {
      identifier: location.identifier,
      label: parentPath === '' ? location.name : `${parentPath}${PATH_SEPARATOR}${location.name}`,
      name: location.name,
      parentPath,
    };
  });
}
