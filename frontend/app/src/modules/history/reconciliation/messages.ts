import type { ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import { type MessageKey, msg } from '@/message-key';
import {
  amountsFor,
  type DisplayStatus,
  type HeadlineKind,
  isHistoryFree,
} from '@/modules/history/reconciliation/use-reconciliation-rows';

export const STATUS_LABEL: Record<DisplayStatus, MessageKey> = {
  blocked: msg.$t('data_issues.reconciliation.status.blocked'),
  matches: msg.$t('data_issues.reconciliation.status.matches'),
  mismatch: msg.$t('data_issues.reconciliation.status.mismatch'),
  not_checked: msg.$t('data_issues.reconciliation.status.not_checked'),
};

export const ACCOUNT_SUMMARY_LABEL: Record<'blocked' | 'hidden' | 'mismatch' | 'not_checked' | 'reconciled', MessageKey> = {
  blocked: msg.$t('data_issues.reconciliation.account_summary.blocked'),
  hidden: msg.$t('data_issues.reconciliation.account_summary.hidden'),
  mismatch: msg.$t('data_issues.reconciliation.account_summary.mismatch'),
  not_checked: msg.$t('data_issues.reconciliation.account_summary.not_checked'),
  reconciled: msg.$t('data_issues.reconciliation.account_summary.reconciled'),
};

export const HEADLINE_LABEL: Record<HeadlineKind, MessageKey> = {
  blocked: msg.$t('data_issues.reconciliation.headline.blocked'),
  matches: msg.$t('data_issues.reconciliation.headline.matches'),
  mismatch: msg.$t('data_issues.reconciliation.headline.mismatch'),
  never: msg.$t('data_issues.reconciliation.headline.never'),
  nothing_checkable: msg.$t('data_issues.reconciliation.headline.nothing_checkable'),
  partial: msg.$t('data_issues.reconciliation.headline.partial'),
};

export const SUBLINE_LABEL: Record<'blocked' | 'matches' | 'not_checked', MessageKey> = {
  blocked: msg.$t('data_issues.reconciliation.subline.blocked'),
  matches: msg.$t('data_issues.reconciliation.subline.matches'),
  not_checked: msg.$t('data_issues.reconciliation.subline.not_checked'),
};

const REASON_LABEL: Record<string, MessageKey> = {
  asset_coverage_missing: msg.$t('data_issues.reconciliation.reason.asset_coverage_missing'),
  blocked: msg.$t('data_issues.reconciliation.reason.blocked'),
  derived_history_stale: msg.$t('data_issues.reconciliation.reason.derived_history_stale'),
  derived_snapshot_changed: msg.$t('data_issues.reconciliation.reason.derived_snapshot_changed'),
  exchange: msg.$t('data_issues.reconciliation.reason.exchange'),
  history_not_synced: msg.$t('data_issues.reconciliation.reason.history_not_synced'),
  history_pending_decoding: msg.$t('data_issues.reconciliation.reason.history_pending_decoding'),
  matches: msg.$t('data_issues.reconciliation.reason.matches'),
  mismatch_higher: msg.$t('data_issues.reconciliation.reason.mismatch_higher'),
  mismatch_history_free: msg.$t('data_issues.reconciliation.reason.mismatch_history_free'),
  mismatch_lower: msg.$t('data_issues.reconciliation.reason.mismatch_lower'),
  never_compared: msg.$t('data_issues.reconciliation.reason.never_compared'),
  non_evm_chain: msg.$t('data_issues.reconciliation.reason.non_evm_chain'),
  observation_missing: msg.$t('data_issues.reconciliation.reason.observation_missing'),
  observation_stale: msg.$t('data_issues.reconciliation.reason.observation_stale'),
  observation_superseded: msg.$t('data_issues.reconciliation.reason.observation_superseded'),
  protocol_bucket: msg.$t('data_issues.reconciliation.reason.protocol_bucket'),
  queries_disabled: msg.$t('data_issues.reconciliation.reason.queries_disabled'),
  rebasing: msg.$t('data_issues.reconciliation.reason.rebasing'),
  result_expired: msg.$t('data_issues.reconciliation.reason.result_expired'),
  unknown_not_compared: msg.$t('data_issues.reconciliation.reason.unknown_not_compared'),
  unknown_pending: msg.$t('data_issues.reconciliation.reason.unknown_pending'),
  unsupported_location: msg.$t('data_issues.reconciliation.reason.unsupported_location'),
};

const PENDING_REASON_PRIORITY = [
  'history_pending_decoding',
  'history_not_synced',
  'asset_coverage_missing',
  'observation_missing',
  'observation_stale',
  'derived_snapshot_changed',
  'derived_history_stale',
  'observation_superseded',
  'result_expired',
  'never_compared',
] as const;

const NOT_COMPARED_REASON_PRIORITY = [
  'exchange',
  'non_evm_chain',
  'protocol_bucket',
  'queries_disabled',
  'rebasing',
  'unsupported_location',
] as const;

function mismatchLabel(bucket: ReconciliationBucket): MessageKey {
  if (isHistoryFree(bucket))
    return REASON_LABEL.mismatch_history_free;

  const { derived, observed } = amountsFor(bucket);
  return derived && observed?.gt(derived)
    ? REASON_LABEL.mismatch_higher
    : REASON_LABEL.mismatch_lower;
}

/**
 * The sentence explaining a row.
 *
 * @remarks
 * `pending` and `not_compared` are different questions - the first can finish, the second is not
 * supported - so they are never collapsed into one vague sentence. Unknown reasons from a newer
 * backend fall back to a neutral sentence for their status instead of failing the page.
 */
export function reasonLabel(bucket: ReconciliationBucket): MessageKey {
  if (bucket.status === 'reconciled')
    return REASON_LABEL.matches;

  if (bucket.status === 'blocked')
    return REASON_LABEL.blocked;

  if (bucket.status === 'mismatch')
    return mismatchLabel(bucket);

  const priority = bucket.status === 'pending' ? PENDING_REASON_PRIORITY : NOT_COMPARED_REASON_PRIORITY;
  const reason = priority.find(candidate => bucket.reasons.includes(candidate));
  if (reason)
    return REASON_LABEL[reason];

  return bucket.status === 'pending' ? REASON_LABEL.unknown_pending : REASON_LABEL.unknown_not_compared;
}
