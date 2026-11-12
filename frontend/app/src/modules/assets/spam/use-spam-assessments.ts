import type { MaybeRefOrGetter, Ref } from 'vue';
import { startPromise } from '@shared/utils';
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

function splitBatches(tokens: SpamPredictionToken[]): SpamPredictionToken[][] {
  const batches: SpamPredictionToken[][] = [];
  for (let index = 0; index < tokens.length; index += SPAM_PREDICTION_BATCH_SIZE)
    batches.push(tokens.slice(index, index + SPAM_PREDICTION_BATCH_SIZE));

  return batches;
}

/**
 * Classifies only the tokens of the page currently handed in.
 *
 * @remarks
 * Nothing is inferred for stored tokens outside the page. When the page, the transaction context
 * or the session changes, the previous scores are dropped before the new request starts, so a row
 * never shows a score that belonged to another page or another user. A failed request leaves the
 * table rows untouched and reports the score for its own batch as unavailable. The backend rejects
 * an empty transaction reference, so a missing or empty one is left out of the request.
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

  let latestRequest = 0;
  let lastPage: SpamPredictionToken[] | undefined;
  let lastSignature: string | undefined;
  let lastSession: number | undefined;

  const pageSignature = computed<string>(() => toValue(tokens)
    .map(token => `${token.identifier}\u{0}${token.txReference ?? ''}`)
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

    if (page.length === 0 || !hasLiveSession()) {
      clearScores();
      return;
    }

    const session = get(liveSessionKey());

    const loading: Record<string, SpamAssessment> = {};
    for (const token of page)
      loading[token.identifier] = { status: 'loading' };

    set(assessments, loading);
    set(status, 'loading');

    const batches = splitBatches(page);
    const outcomes = await Promise.all(batches.map(async batch =>
      fromRequest(async () => predictSpam(batch.map(({ identifier, txReference }) => (txReference ? { identifier, txReference } : { identifier })))),
    ));

    if (request !== latestRequest || signature !== get(pageSignature) || session !== get(liveSessionKey()))
      return;

    const resolved: Record<string, SpamAssessment> = {};
    let anyUnavailable = false;

    batches.forEach((batch, index) => {
      const outcome = outcomes[index];
      for (const { identifier } of batch) {
        if (!outcome.ok) {
          anyUnavailable = true;
          resolved[identifier] = { status: 'unavailable' };
          continue;
        }

        const prediction = outcome.value[identifier];
        if (prediction === null) {
          resolved[identifier] = { status: 'unsupported' };
        }
        else if (prediction === undefined) {
          anyUnavailable = true;
          resolved[identifier] = { status: 'unavailable' };
        }
        else {
          resolved[identifier] = { prediction, status: 'ready' };
        }
      }
    });

    set(assessments, resolved);
    set(status, anyUnavailable ? 'unavailable' : 'ready');
  }

  function onSourcesChanged(): void {
    const page = toValue(tokens);
    const signature = get(pageSignature);
    const session = get(liveSessionKey());

    if (page === lastPage && signature === lastSignature && session === lastSession)
      return;

    lastPage = page;
    lastSignature = signature;
    lastSession = session;
    startPromise(refresh());
  }

  watch([(): SpamPredictionToken[] => toValue(tokens), pageSignature, liveSessionKey()], onSourcesChanged, { flush: 'sync', immediate: true });

  return {
    assessments: shallowReadonly(assessments),
    status: shallowReadonly(status),
  };
}
