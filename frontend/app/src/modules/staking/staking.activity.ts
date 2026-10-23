import { msg } from '@/message-key';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart, type ActivityText } from '@/modules/task-center/core/types';

/** The staking locations whose rows load through `useStakingRows`. */
export type StakingRowsPart = typeof ActivityPart.HYPERLIQUID | typeof ActivityPart.SOLANA;

/** One validator being added, as the validator form submits it. */
export interface ValidatorAddSubject {
  readonly publicKey?: string;
  readonly validatorIndex?: string;
}

/**
 * What names the validator: its public key, else its index.
 *
 * @remarks
 * An empty field counts as absent. The form hands back every field, so an addition by index alone
 * arrives with `publicKey: ''`, and treating that as a key collapsed every index-only addition onto
 * one id.
 */
function validatorOf(subject: ValidatorAddSubject): string {
  const { publicKey, validatorIndex } = subject;
  if (publicKey)
    return publicKey;
  return validatorIndex ?? '';
}

/**
 * Adding one validator, keyed by it so two additions never dedup.
 *
 * @remarks
 * The validator list and the staking performance go stale on the `add` prefix, so any addition
 * marks both for a reload.
 */
export const validatorAddActivity = defineActivity<ValidatorAddSubject, readonly [string]>({
  key: subject => [validatorOf(subject)],
  kind: ActivityKind.STAKING,
  part: ActivityPart.ADD,
});

/**
 * The subtitle a validator addition renders under, beside the id it belongs to, for the same
 * reason `accountActivityLabel` sits beside the account descriptors.
 */
export function validatorAddLabel(subject: ValidatorAddSubject): ActivityText {
  const validator = validatorOf(subject);
  return activityLabelFor(msg.$t('task_center.activity.staking.add_validator'), {
    validator: validator ? truncateAddress(validator) : '',
  });
}

/** Loading the ETH validator list. */
export const validatorsActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.STAKING,
  part: ActivityPart.VALIDATORS,
});

/** Refreshing the ETH staking performance. */
export const stakingPerformanceActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.STAKING,
  part: ActivityPart.PERFORMANCE,
});

/**
 * Refreshing the Kraken staking events.
 *
 * @remarks
 * A stats-price backfill the backend runs for the `kraken` counterparty reports its progress here,
 * since this query is the only work running while those frames arrive.
 */
export const krakenStakingActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.STAKING,
  part: ActivityPart.KRAKEN,
});

/**
 * Loading one location's staking rows. The location is the whole key, narrowed to the locations
 * that load this way, so it can never land on the id of a Kraken or validator activity.
 */
export const stakingRowsActivity = defineActivity<{ part: StakingRowsPart }, readonly [StakingRowsPart]>({
  key: subject => [subject.part],
  kind: ActivityKind.STAKING,
});
