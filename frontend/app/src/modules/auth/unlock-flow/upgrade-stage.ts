import { UnlockPhase } from './use-unlock-flow';

/**
 * Whether the unlock got past the DB upgrade: the session is loading or ready, so the upgrade
 * screen reports the run finished.
 */
export function isUpgradeCompleted(phase: string): boolean {
  return phase === UnlockPhase.loadingSession || phase === UnlockPhase.ready;
}

/**
 * Whether an unlock in this phase shows the DB upgrade screen: while the upgrade runs, through the
 * session load that follows it as the "upgraded" handoff, and after a failure it caused.
 *
 * @param phase - the unlock flow's current phase
 * @param upgradeVisible - whether upgrade or migration progress has arrived for this unlock
 * @param upgradeFailed - whether the unlock failed while that progress was on screen
 */
export function showsUpgrade(phase: string, upgradeVisible: boolean, upgradeFailed: boolean): boolean {
  if (!upgradeVisible)
    return false;
  if (phase === UnlockPhase.error)
    return upgradeFailed;
  return phase === UnlockPhase.unlocking || isUpgradeCompleted(phase);
}
