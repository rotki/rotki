import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { computed, type MaybeRefOrGetter, type Ref, ref, shallowReadonly, shallowRef, toValue, watch } from 'vue';
import { SPAM_PREDICTION_BATCH_SIZE, type SpamPrediction, type SpamPredictionToken, useAssetSpamPredictionApi } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { fromRequest } from '@/modules/core/api/request-result';
import { hasLiveSession, liveSessionKey } from '@/modules/core/session/session-lifecycle';

/** The estimate state for one row of the currently displayed page. */
export type SpamAssessment =
  | { status: 'loading' }
  | { status: 'ready'; prediction: SpamPrediction }
  | { status: 'unsupported' }
  | { status: 'unavailable' };

type SpamAssessmentStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

interface UseSpamAssessmentsReturn {
  assessments: Readonly<Ref<Record<string, SpamAssessment>>>;
  status: Readonly<Ref<SpamAssessmentStatus>>;
}

const EVM_NAMESPACE_PREFIX = 'eip155:';
const ERC20_TOKEN_SEGMENT = '/erc20:';

/**
 * Whether an asset identifier is an EVM ERC-20 token that the spam model can assess.
 *
 * @remarks
 * Colibri's spam prediction endpoint only scores ERC-20 tokens (`eip155:<chain>/erc20:<address>`).
 * Filtering by identifier lets callers that do not hold full `SupportedAsset` metadata skip native
 * coins, NFTs, and non-EVM assets instead of requesting unsupported lookups.
 */
export function isErc20TokenIdentifier(identifier?: string | null): identifier is string {
  if (typeof identifier !== 'string' || !identifier.startsWith(EVM_NAMESPACE_PREFIX))
    return false;

  const segmentIndex = identifier.indexOf(ERC20_TOKEN_SEGMENT);
  return segmentIndex > EVM_NAMESPACE_PREFIX.length
    && segmentIndex + ERC20_TOKEN_SEGMENT.length < identifier.length;
}

function tokenCacheKey(token: SpamPredictionToken): string {
  return `${token.identifier}\u{0}${token.txReference ?? ''}`;
}

function splitBatches(tokens: SpamPredictionToken[]): SpamPredictionToken[][] {
  const batches: SpamPredictionToken[][] = [];
  for (let index = 0; index < tokens.length; index += SPAM_PREDICTION_BATCH_SIZE)
    batches.push(tokens.slice(index, index + SPAM_PREDICTION_BATCH_SIZE));

  return batches;
}

function partitionPage(
  page: SpamPredictionToken[],
  cache: Map<string, SpamAssessment>,
): { initialAssessments: Record<string, SpamAssessment>; uncachedTokens: SpamPredictionToken[] } {
  const initialAssessments: Record<string, SpamAssessment> = {};
  const uncachedTokens: SpamPredictionToken[] = [];
  const queuedKeys = new Set<string>();

  for (const token of page) {
    const key = tokenCacheKey(token);
    const cached = cache.get(key);
    if (cached) {
      initialAssessments[token.identifier] = cached;
      continue;
    }

    initialAssessments[token.identifier] = { status: 'loading' };
    if (!queuedKeys.has(key)) {
      queuedKeys.add(key);
      uncachedTokens.push(token);
    }
  }

  return { initialAssessments, uncachedTokens };
}

function mergeBatchOutcomes(
  batches: SpamPredictionToken[][],
  outcomes: Awaited<ReturnType<typeof fromRequest<Record<string, SpamPrediction | null>>>>[],
  initialAssessments: Record<string, SpamAssessment>,
  cache: Map<string, SpamAssessment>,
): { anyUnavailable: boolean; merged: Record<string, SpamAssessment> } {
  const merged: Record<string, SpamAssessment> = { ...initialAssessments };
  let anyUnavailable = false;

  batches.forEach((batch, index) => {
    const outcome = outcomes[index];
    for (const token of batch) {
      const prediction = outcome.ok ? outcome.value[token.identifier] : undefined;
      if (prediction === undefined) {
        anyUnavailable = true;
        merged[token.identifier] = { status: 'unavailable' };
        continue;
      }

      const entry: SpamAssessment = prediction === null
        ? { status: 'unsupported' }
        : { prediction, status: 'ready' };
      cache.set(tokenCacheKey(token), entry);
      merged[token.identifier] = entry;
    }
  });

  return { anyUnavailable, merged };
}

/**
 * Classifies only the tokens of the page currently handed in, caching completed outcomes per session.
 *
 * @remarks
 * Nothing is inferred for stored tokens outside the page. Previously resolved `ready` and
 * `unsupported` entries are reused across page updates within the same session as long as their
 * `(identifier, txReference)` pair matches; `unavailable` entries are not cached so later changes
 * can retry them. When the session ends or changes, cached entries and scores are dropped so a row
 * never shows a score that belonged to another user. The backend rejects an empty transaction
 * reference, so a missing or empty one is left out of the request.
 *
 * @param tokens - The page's tokens. Callers pass only tokens the model can assess (EVM tokens);
 * anything else is answered as unsupported after a pointless lookup.
 */
export function useSpamAssessments(
  tokens: MaybeRefOrGetter<SpamPredictionToken[]>,
): UseSpamAssessmentsReturn {
  const { predictSpam } = useAssetSpamPredictionApi();

  const assessments = ref<Record<string, SpamAssessment>>({});
  const status = shallowRef<SpamAssessmentStatus>('idle');
  const cache = new Map<string, SpamAssessment>();

  let latestRequest = 0;
  let lastSignature: string | undefined;
  let lastSession: number | undefined;

  const pageSignature = computed<string>(() => toValue(tokens)
    .map(tokenCacheKey)
    .join('\u{1}'));

  function clearScores(): void {
    latestRequest += 1;
    set(assessments, {});
    set(status, 'idle');
  }

  async function refresh(): Promise<void> {
    const page = toValue(tokens);
    const signature = get(pageSignature);
    const request = ++latestRequest;

    if (!hasLiveSession()) {
      cache.clear();
      clearScores();
      return;
    }

    if (page.length === 0) {
      clearScores();
      return;
    }

    const session = get(liveSessionKey());
    const { initialAssessments, uncachedTokens } = partitionPage(page, cache);

    if (uncachedTokens.length === 0) {
      set(assessments, initialAssessments);
      set(status, 'ready');
      return;
    }

    set(assessments, initialAssessments);
    set(status, 'loading');

    const batches = splitBatches(uncachedTokens);
    const outcomes = await Promise.all(batches.map(async batch =>
      fromRequest(async () => predictSpam(batch.map(({ identifier, txReference }) => (txReference ? { identifier, txReference } : { identifier })))),
    ));

    if (request !== latestRequest || signature !== get(pageSignature) || session !== get(liveSessionKey()))
      return;

    const { anyUnavailable, merged } = mergeBatchOutcomes(batches, outcomes, initialAssessments, cache);
    set(assessments, merged);
    set(status, anyUnavailable ? 'unavailable' : 'ready');
  }

  function onSourcesChanged(): void {
    const signature = get(pageSignature);
    const session = get(liveSessionKey());

    if (signature === lastSignature && session === lastSession)
      return;

    if (!hasLiveSession() || session !== lastSession)
      cache.clear();

    lastSignature = signature;
    lastSession = session;
    startPromise(refresh());
  }

  watch([pageSignature, liveSessionKey()], onSourcesChanged, { flush: 'sync', immediate: true });

  return {
    assessments: shallowReadonly(assessments),
    status: shallowReadonly(status),
  };
}
