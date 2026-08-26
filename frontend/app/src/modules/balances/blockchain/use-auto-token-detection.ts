import { logger } from '@/modules/core/common/logging/logging';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseAutoTokenDetectionReturn {
  /**
   * Runs `pass`, telling it whether this login is due a detection sweep, and owns the cooldown
   * bookkeeping around it.
   *
   * @remarks
   * Detection is a stage inside each chain job, so nothing here detects anything: this answers
   * "is a sweep due?" and records that one happened, and `pass` decides what detecting means.
   */
  withDetection: <T>(pass: (detect: boolean) => Promise<T>) => Promise<T>;
  skipReason: () => string | null;
}

const HOUR_IN_MS = 60 * 60 * 1000;

export function useAutoTokenDetection(): UseAutoTokenDetectionReturn {
  const autoDetectTokensCooldownHours = useSetting('autoDetectTokensCooldownHours');
  const autoDetectTokensOnLogin = useSetting('autoDetectTokensOnLogin');
  const lastAutoDetectAt = useSetting('lastAutoDetectAt');
  const { updateFrontendSetting } = useSettingsOperations();

  const inFlight = shallowRef<boolean>(false);

  function isCooldownElapsed(): boolean {
    const now = Date.now();
    const lastAt = get(lastAutoDetectAt);
    // Clock-skew guard: if the stored timestamp is in the future
    // (DB restore, clock rollback), treat it as never-run.
    const elapsed = lastAt > now ? Number.POSITIVE_INFINITY : now - lastAt;
    const cooldownMs = get(autoDetectTokensCooldownHours) * HOUR_IN_MS;
    return elapsed >= cooldownMs;
  }

  function skipReason(): string | null {
    if (get(inFlight))
      return 'already in-flight';
    if (!get(autoDetectTokensOnLogin))
      return 'auto-detect-tokens-on-login disabled';
    if (!isCooldownElapsed()) {
      const lastAt = get(lastAutoDetectAt);
      const remainingMs = get(autoDetectTokensCooldownHours) * HOUR_IN_MS - (Date.now() - lastAt);
      return `within cooldown (${Math.round(remainingMs / 60_000)}m remaining)`;
    }
    return null;
  }

  async function withDetection<T>(pass: (detect: boolean) => Promise<T>): Promise<T> {
    const skip = skipReason();
    if (skip !== null) {
      logger.debug(`Auto token detection skipped: ${skip}`);
      return pass(false);
    }

    const now = Date.now();
    logger.info('Auto token detection: running');

    set(inFlight, true);
    try {
      return await pass(true);
    }
    finally {
      // Always persist the timestamp, even on failure, so a persistently broken
      // chain doesn't trigger detection on every login.
      await updateFrontendSetting({ lastAutoDetectAt: now });
      set(inFlight, false);
      logger.debug(`Auto token detection: persisted lastAutoDetectAt=${now}`);
    }
  }

  return { skipReason, withDetection };
}
