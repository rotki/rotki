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
 * One observed fact about the token, identified by a stable code the frontend translates.
 *
 * @remarks
 * `value` is only present for the transfer-count codes.
 */
const SpamSignal = z.object({
  code: z.enum([
    'non_ascii',
    'invisible_characters',
    'combining_marks',
    'mixed_scripts',
    'url',
    'promotion',
    'common_symbol',
    'lookalike_symbol',
    'known_origin_unavailable',
    'max_token_transfers',
    'mean_token_transfers',
    'in_packaged_globaldb',
    'not_in_packaged_globaldb',
    'in_collection',
    'not_in_collection',
  ]),
  field: z.enum(['name', 'symbol', 'context']),
  value: z.number().optional(),
});

export type SpamSignal = z.infer<typeof SpamSignal>;

/**
 * One token's local-model output.
 *
 * @remarks
 * `spamProbability` is a model estimate, not a verdict: it says nothing about whether the asset is
 * authentic, only how strongly the model associates its locally known metadata with spam.
 * `flagged` is the backend's decision against `threshold`; read it rather than comparing again.
 */
export const SpamPrediction = z.object({
  flagged: z.boolean(),
  modelReasons: z.array(SpamPredictionReason),
  observedSignals: z.array(SpamSignal),
  spamProbability: z.number().min(0).max(1),
  threshold: z.number().min(0).max(1),
});

export type SpamPrediction = z.infer<typeof SpamPrediction>;

/**
 * The result keyed by the exact requested identifier. A `null` entry means the backend could not
 * assess that token; a missing entry is a contract violation and is treated as unavailable.
 *
 * @remarks
 * The keys are asset identifiers and must reach the caller byte for byte, so the request skips the
 * camel-casing of root keys.
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
        skipRootCamelCase: true,
        target: RequestTarget.COLIBRI,
      },
    );
    return SpamPredictionResponse.parse(response);
  };

  return { predictSpam };
}
