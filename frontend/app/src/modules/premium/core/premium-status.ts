import type { PremiumStatusUpdateData } from '@/modules/core/messaging/types/shared-types';
import { PremiumInactiveCause } from '@/modules/shell/action-center/use-raised-conditions-store';

/** What a premium status message says: active, or inactive and why. */
export type PremiumStatus =
  | { active: true }
  | { active: false; cause: PremiumInactiveCause; reason?: string };

/**
 * Reads a premium status message.
 *
 * @remarks
 * The backend sends one only while premium credentials are saved, so an inactive message always
 * means a saved key that does not work. A `reason` comes with a device limit and is the backend's own
 * explanation; `expired` marks a rejected key; with neither, the server could not be reached.
 */
export function readPremiumStatus({ expired, isPremiumActive, reason }: PremiumStatusUpdateData): PremiumStatus {
  if (isPremiumActive)
    return { active: true };

  if (reason)
    return { active: false, cause: PremiumInactiveCause.DEVICE_LIMIT, reason };

  return { active: false, cause: expired ? PremiumInactiveCause.EXPIRED : PremiumInactiveCause.UNREACHABLE };
}
