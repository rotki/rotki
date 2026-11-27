import type { SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { get } from '@vueuse/shared';
import { computed, type MaybeRefOrGetter, type Ref, toValue } from 'vue';
import { isErc20TokenIdentifier, type SpamAssessment, useSpamAssessments } from '@/modules/assets/spam/use-spam-assessments';

/** Matches an EVM transaction hash, either bare or prefixed with its chain ID in a group identifier. */
const EVM_GROUP_TX_HASH = /^(?:\d+)?(0x[0-9a-f]{64})$/i;
const RAW_TX_HASH = /^[0-9a-f]{64}$/i;

function extractEvmTxHash(value: unknown): string | undefined {
  if (typeof value !== 'string')
    return undefined;

  const trimmed = value.trim();
  const prefixed = EVM_GROUP_TX_HASH.exec(trimmed);
  if (prefixed)
    return prefixed[1];

  return RAW_TX_HASH.test(trimmed) ? trimmed : undefined;
}

function issueTxReference(issue: DataIssue): string | undefined {
  return extractEvmTxHash(issue.groupIdentifier)
    ?? extractEvmTxHash(issue.payload?.groupIdentifier)
    ?? extractEvmTxHash(issue.payload?.txRef);
}

/**
 * Builds deduplicated ERC-20 prediction entries from a page of data issues.
 *
 * @remarks
 * Multiple issues can point at the same token; deduplicating avoids redundant batch slots, and
 * preferring an entry with a valid EVM transaction hash gives Colibri receipt context when any
 * issue on the page carries one.
 */
export function toDataIssueSpamTokens(issues: readonly DataIssue[]): SpamPredictionToken[] {
  const byIdentifier = new Map<string, SpamPredictionToken>();

  for (const issue of issues) {
    if (!isErc20TokenIdentifier(issue.asset))
      continue;

    const txReference = issueTxReference(issue);
    const existing = byIdentifier.get(issue.asset);
    if (!existing) {
      byIdentifier.set(issue.asset, txReference ? { identifier: issue.asset, txReference } : { identifier: issue.asset });
    }
    else if (!existing.txReference && txReference) {
      byIdentifier.set(issue.asset, { identifier: issue.asset, txReference });
    }
  }

  return Array.from(byIdentifier.values());
}

interface UseDataIssuesSpamAssessmentsReturn {
  readonly assessments: Readonly<Ref<Record<string, SpamAssessment>>>;
  readonly getSpamAssessment: (asset?: string | null) => SpamAssessment | undefined;
}

/**
 * Assesses the ERC-20 tokens referenced by the supplied data issues.
 */
export function useDataIssuesSpamAssessments(
  issues: MaybeRefOrGetter<readonly DataIssue[]>,
): UseDataIssuesSpamAssessmentsReturn {
  const spamTokens = computed<SpamPredictionToken[]>(() => toDataIssueSpamTokens(toValue(issues)));
  const { assessments } = useSpamAssessments(spamTokens);

  function getSpamAssessment(asset?: string | null): SpamAssessment | undefined {
    return asset ? get(assessments)[asset] : undefined;
  }

  return {
    assessments,
    getSpamAssessment,
  };
}
