import type { SettingsHighlightId } from '@/modules/settings/setting-highlight-ids';
import type { RegistryEntry } from '@/modules/settings/settings-channels';
import { accountingRegistry } from '@/modules/settings/settings-registry-accounting';
import { frontendRegistry } from '@/modules/settings/settings-registry-frontend';
import { generalRegistry } from '@/modules/settings/settings-registry-general';
import { sessionRegistry } from '@/modules/settings/settings-registry-session';

/**
 * Single source of truth for every setting, composed from the per-channel slices. Each slice declares
 * its entries with its channel builder, which validates the wire key against that channel's settings
 * type at compile time (a typo or stale field name fails to build) and types
 * `encode`/`mirror`/`effects`/`project` against that field. `useSetting` derives read routing,
 * `settingsWriter` derives write routing, and `SettingValue` derives the value type, all from here.
 */
export const settingsRegistry = {
  ...generalRegistry,
  ...frontendRegistry,
  ...sessionRegistry,
  ...accountingRegistry,
} satisfies Record<string, RegistryEntry>;

/**
 * Registry keyed for dynamic (unregistered-key-tolerant) lookup. A `Map` built from `Object.entries`
 * types its values as `RegistryEntry` without any assertion, so consumers that resolve an entry from
 * an arbitrary `string` (the write dispatcher, the repo's effect runner) go through here instead of
 * casting `settingsRegistry` to a `Record` at each call site.
 */
const registryByKey: ReadonlyMap<string, RegistryEntry> = new Map(Object.entries(settingsRegistry));

/** Resolves a registry entry from an arbitrary string key, or `undefined` if the key is not registered. */
export function getRegistryEntry(key: string): RegistryEntry | undefined {
  return registryByKey.get(key);
}

/** All registry entries as typed `[logicalKey, entry]` pairs (a bare `Object.entries` widens to a union). */
export function registryEntries(): ReadonlyArray<readonly [string, RegistryEntry]> {
  return [...registryByKey];
}

/**
 * Reverse index: the logical keys that share a given settings-search anchor. Built once from the
 * registry so it cannot drift; composite anchors return several keys, keyless anchors return `[]`.
 */
const keysByAnchor: ReadonlyMap<SettingsHighlightId, readonly string[]> = ((): ReadonlyMap<SettingsHighlightId, readonly string[]> => {
  const map = new Map<SettingsHighlightId, string[]>();
  for (const [key, entry] of registryByKey) {
    const { anchor } = entry;
    if (!anchor)
      continue;
    const keys = map.get(anchor) ?? [];
    keys.push(key);
    map.set(anchor, keys);
  }
  return map;
})();

/** The registry keys anchored to `anchor` (empty for keyless anchors such as action targets). */
export function registryKeysForAnchor(anchor: SettingsHighlightId): readonly string[] {
  return keysByAnchor.get(anchor) ?? [];
}
