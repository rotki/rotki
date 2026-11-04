/**
 * A request with its location filter covering the locations below it: filtering Banks means every
 * bank, and filtering a leaf is unaffected.
 */
export function withLocationScope<T extends { readonly location?: string | string[] }>(payload: T): T & { readonly locationScope?: 'subtree' } {
  return payload.location === undefined ? payload : { ...payload, locationScope: 'subtree' };
}
