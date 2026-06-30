import dayjs from 'dayjs';
import { useMainStore } from '@/modules/core/common/use-main-store';

const DAY_KEY = 'rotki.asset_update_check.day';
const VERSION_KEY = 'rotki.asset_update_check.version';

export interface AssetUpdateThrottle {
  shouldCheck: () => boolean;
  recordCheck: () => void;
}

/**
 * Throttles the automatic asset-update check on login. Asset updates ship from the
 * `rotki/data` repo on a days-to-weeks cadence, so checking on every login is wasteful.
 * The network check only runs on the first login of a calendar day, or whenever the
 * rotki app version changed since the last check (a new build may expect a newer asset
 * DB). The manual Settings check bypasses this entirely.
 */
export function useAssetUpdateThrottle(): AssetUpdateThrottle {
  const lastDay = useLocalStorage<string>(DAY_KEY, '');
  const lastVersion = useLocalStorage<string>(VERSION_KEY, '');
  const { appVersion } = storeToRefs(useMainStore());

  const today = (): string => dayjs().format('YYYY-MM-DD');

  return {
    recordCheck: (): void => {
      set(lastDay, today());
      set(lastVersion, get(appVersion));
    },
    shouldCheck: (): boolean => get(lastDay) !== today() || get(lastVersion) !== get(appVersion),
  };
}
