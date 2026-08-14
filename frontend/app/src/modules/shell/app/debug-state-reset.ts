import { DebugStateGroup } from '@shared/ipc';
import { logger } from '@/modules/core/common/logging/logging';

/**
 * A group is matched by exact key, by suffix, and by prefix. Both partial forms
 * exist because several keys embed the logged user id or username, which only
 * the renderer knows and which changes between logins: some put it in front
 * (`<userId>.rotki_query_status`), others append it
 * (`rotki.migrated_addresses.<identifier>`).
 */
interface AreaKeys {
  readonly exact?: readonly string[];
  readonly suffixes?: readonly string[];
  readonly prefixes?: readonly string[];
}

interface GroupDefinition {
  readonly local?: AreaKeys;
  readonly session?: AreaKeys;
}

/**
 * Deliberately excluded from every group, because wiping them costs more than it
 * saves during development: `rotki.backend_url*` (points the app at a custom
 * backend), the login memory (`rotki.username`, `rotki.remember_*`), and the
 * plain preferences (theme, language, animations, table sorting/filters).
 */
const DEBUG_STATE_GROUPS: Record<DebugStateGroup, GroupDefinition> = {
  [DebugStateGroup.FIRST_RUN]: {
    local: {
      exact: [
        'rotki.last_version', // release notes popup
        'rotki.airdrops.hide_unknown_alert',
        'rotki.asset_update_check.day', // asset update throttle
        'rotki.asset_update_check.version',
        'rotki_skip_asset_db_version',
      ],
      suffixes: [
        '.rotki_query_status', // `<userId>.rotki_query_status`, dismissed query status
      ],
    },
    session: {
      exact: [
        'rotki.messages.welcome', // cached dynamic messages
        'rotki.messages.dashboard',
        'rotki.messages.dash.dismissed',
        'rotki.update_available',
        'rotki.notification.last_display',
        'skip_update',
      ],
      prefixes: [
        'rotki.migrated_addresses.', // `rotki.migrated_addresses.<identifier>`, dismissed new-accounts notice
      ],
    },
  },
};

function matchingKeys(storage: Storage, keys: AreaKeys): string[] {
  const exact = new Set(keys.exact ?? []);
  const suffixes = keys.suffixes ?? [];
  const prefixes = keys.prefixes ?? [];
  const matched: string[] = [];

  // Collected in full before removing anything: removal reindexes the storage.
  for (let index = 0; index < storage.length; index++) {
    const key = storage.key(index);
    if (key === null)
      continue;

    const isMatch = exact.has(key)
      || suffixes.some(suffix => key.endsWith(suffix))
      || prefixes.some(prefix => key.startsWith(prefix));

    if (isMatch)
      matched.push(key);
  }

  return matched;
}

function clearArea(storage: Storage, keys: AreaKeys | undefined): string[] {
  if (!keys)
    return [];

  const matched = matchingKeys(storage, keys);
  matched.forEach(key => storage.removeItem(key));
  return matched;
}

/**
 * Wipes the browser-storage keys of a debug group and returns what was removed.
 *
 * The caller has to reload afterwards: the `useLocalStorage`/`useSessionStorage`
 * refs hold their value in memory and write it back on the next change, so a
 * reset without a reload is invisible and gets undone.
 */
export function resetDebugState(group: DebugStateGroup): string[] {
  const definition = DEBUG_STATE_GROUPS[group];
  if (!definition) {
    logger.warn(`unknown debug state group: ${group}`);
    return [];
  }

  const removed = [
    ...clearArea(localStorage, definition.local),
    ...clearArea(sessionStorage, definition.session),
  ];

  logger.info(`reset debug state group ${group}, removed ${removed.length} keys`, removed);
  return removed;
}
