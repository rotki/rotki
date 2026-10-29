/** Which locations a location filter selects: the location alone, or it and every location below it. */
export const LocationScope = {
  EXACT: 'exact',
  SUBTREE: 'subtree',
} as const;

export type LocationScope = typeof LocationScope[keyof typeof LocationScope];

interface LocationFiltered {
  readonly location?: string | string[];
  readonly locationScope?: LocationScope;
}

/**
 * A request with its location filter covering the locations below it, unless it asks for the
 * exact location: filtering Banks means every bank, and filtering a leaf is unaffected.
 */
export function withLocationScope<T extends LocationFiltered>(payload: T): T {
  if (payload.location === undefined || payload.locationScope !== undefined)
    return payload;
  return { ...payload, locationScope: LocationScope.SUBTREE };
}
