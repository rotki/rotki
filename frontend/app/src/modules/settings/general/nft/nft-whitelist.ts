import { isEqual } from 'es-toolkit';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { getDomain } from '@/modules/core/common/helpers/url';

/**
 * Reads the domains out of what the user typed into the field.
 *
 * @remarks
 * The field takes a comma separated list, and each entry is reduced to its domain, so pasting a
 * full url to an image adds the host it came from rather than the url itself.
 *
 * @param input - the raw field text
 * @returns the domains it named, in the order they were typed
 */
export function parseWhitelistInput(input: string): string[] {
  return input
    .split(',')
    .filter(value => !!value)
    .map(value => getDomain(value.trim()));
}

/**
 * The whitelist as it would be after adding what was typed.
 *
 * @remarks
 * A domain already on the list is not added twice, which is what makes re-adding one a no-op
 * rather than something to save.
 *
 * @param saved - the domains already whitelisted
 * @param added - the domains the field named
 * @returns the two lists merged, saved ones first
 */
export function mergeWhitelist(saved: string[], added: string[]): string[] {
  return [...saved, ...added].filter(uniqueStrings);
}

/**
 * Whether the merged list differs from what is saved, which is what offers the save.
 *
 * @param saved - the domains already whitelisted
 * @param merged - the list after adding what was typed
 * @returns whether there is anything to save
 */
export function hasWhitelistChanges(saved: string[], merged: string[]): boolean {
  return !isEqual(merged, saved);
}
