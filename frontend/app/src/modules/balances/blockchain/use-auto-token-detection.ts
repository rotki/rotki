import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { logger } from '@/modules/core/common/logging/logging';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseAutoTokenDetectionReturn {
  willDetect: () => boolean;
  maybeDetect: () => Promise<void>;
  skipReason: () => string | null;
}

const HOUR_IN_MS = 60 * 60 * 1000;

export function useAutoTokenDetection(): UseAutoTokenDetectionReturn {
  const { detectAllTokens } = useTokenDetectionOrchestrator();
  const { autoDetectTokens } = storeToRefs(useGeneralSettingsStore());
  const { autoDetectTokensCooldownHours, lastAutoDetectAt } = storeToRefs(useFrontendSettingsStore());
  const { updateFrontendSetting } = useSettingsOperations();

  const inFlight = ref<boolean>(false);

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
    if (!get(autoDetectTokens))
      return 'auto-detect-tokens disabled';
    if (!isCooldownElapsed()) {
      const lastAt = get(lastAutoDetectAt);
      const remainingMs = get(autoDetectTokensCooldownHours) * HOUR_IN_MS - (Date.now() - lastAt);
      return `within cooldown (${Math.round(remainingMs / 60_000)}m remaining)`;
    }
    return null;
  }

  function willDetect(): boolean {
    return skipReason() === null;
  }

  async function maybeDetect(): Promise<void> {
    const skip = skipReason();
    if (skip !== null) {
      logger.debug(`Auto token detection skipped: ${skip}`);
      return;
    }

    const now = Date.now();
    logger.info('Auto token detection: running');

    set(inFlight, true);
    try {
      await detectAllTokens();
    }
    catch (error: unknown) {
      logger.error('Auto token detection failed on initial load', error);
    }
    finally {
      // Always persist the timestamp, even on failure, so a persistently broken
      // chain doesn't trigger detection on every login.
      await updateFrontendSetting({ lastAutoDetectAt: now });
      set(inFlight, false);
      logger.debug(`Auto token detection: persisted lastAutoDetectAt=${now}`);
    }
  }

  return { maybeDetect, skipReason, willDetect };
}
