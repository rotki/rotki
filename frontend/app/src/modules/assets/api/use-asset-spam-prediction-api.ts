import { z } from 'zod';
import { RequestTarget } from '@/modules/core/api/constants';
import { api } from '@/modules/core/api/rotki-api';

/** The backend rejects a larger batch, so a page is split into requests of this size. */
export const SPAM_PREDICTION_BATCH_SIZE = 100;

const SpamPredictionReason = z.object({
  feature: z.string(),
  probabilityDelta: z.number(),
  value: z.number(),
});

/**
 * One token's local-model output.
 *
 * @remarks
 * `spamProbability` is a model estimate, not a verdict: it says nothing about whether the asset is
 * authentic, only how strongly the model associates its locally known metadata with spam.
 */
export const SpamPrediction = z.object({
  flagged: z.boolean(),
  modelReasons: z.array(SpamPredictionReason),
  observedSignals: z.array(z.string()),
  spamProbability: z.number().min(0).max(1),
  threshold: z.number().min(0).max(1),
});

export type SpamPrediction = z.infer<typeof SpamPrediction>;

/**
 * The result keyed by the exact requested identifier. A `null` entry means the backend could not
 * assess that token; a missing entry is a contract violation and is treated as unavailable.
 */
export const SpamPredictionResponse = z.record(z.string(), SpamPrediction.nullable());

export type SpamPredictionResponse = z.infer<typeof SpamPredictionResponse>;

export interface SpamPredictionToken {
  identifier: string;
  txReference?: string | null;
}

interface UseAssetSpamPredictionApiReturn {
  predictSpam: (tokens: SpamPredictionToken[]) => Promise<SpamPredictionResponse>;
}

export function useAssetSpamPredictionApi(): UseAssetSpamPredictionApiReturn {
  const predictSpam = async (tokens: SpamPredictionToken[]): Promise<SpamPredictionResponse> => {
    const response = await api.post<unknown>(
      '/assets/spam/predict',
      { tokens },
      {
        target: RequestTarget.COLIBRI,
        // The response is a map keyed by asset identifiers, which must reach us byte for byte.
        skipRootCamelCase: true,
      },
    );
    return SpamPredictionResponse.parse(response);
  };

  return { predictSpam };
}
