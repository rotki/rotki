import type { SpamPrediction, SpamPredictionResponse, SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, type Ref, ref } from 'vue';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import { isErc20TokenIdentifier, useSpamAssessments } from './use-spam-assessments';

const { predictSpam } = vi.hoisted(() => ({
  predictSpam: vi.fn<(tokens: SpamPredictionToken[]) => Promise<SpamPredictionResponse>>(),
}));

vi.mock('@/modules/assets/api/use-asset-spam-prediction-api', () => ({
  SPAM_PREDICTION_BATCH_SIZE: 100,
  useAssetSpamPredictionApi: (): object => ({ predictSpam }),
}));

function token(identifier: string, txReference?: string): SpamPredictionToken {
  return { identifier, txReference };
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolveFn) => {
    resolve = resolveFn;
  });
  return { promise, resolve };
}

function prediction(spamProbability = 0.8, threshold = 0.5): SpamPrediction {
  return {
    flagged: spamProbability >= threshold,
    modelReasons: [{ feature: 'log_transfer_count', probabilityDelta: 0.02, value: 3 }],
    observedSignals: [{ code: 'url', field: 'name' }],
    spamProbability,
    threshold,
  };
}

describe('useSpamAssessments', () => {
  let scopes: EffectScope[] = [];

  function assess(tokens: Ref<SpamPredictionToken[]>): ReturnType<typeof useSpamAssessments> {
    const scope = effectScope();
    scopes.push(scope);
    return scope.run(() => useSpamAssessments(tokens))!;
  }

  beforeEach(() => {
    beginSession();
    predictSpam.mockImplementation(async (tokens: { identifier: string }[]) => Object.fromEntries(
      tokens.map(({ identifier }) => [identifier, prediction()]),
    ));
  });

  afterEach(() => {
    scopes.forEach(scope => scope.stop());
    scopes = [];
    endSession();
    vi.clearAllMocks();
  });

  it('should assess only the supplied page in bounded batches', async () => {
    const page = Array.from({ length: 101 }, (_, index) => token(`eip155:1/erc20:0x${index}`));
    predictSpam.mockImplementation(async (tokens: { identifier: string }[]) => Object.fromEntries(
      tokens.map(({ identifier }) => [identifier, prediction()]),
    ));

    const { assessments } = assess(ref(page));
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledTimes(2);
    expect(predictSpam.mock.calls[0][0]).toHaveLength(100);
    expect(predictSpam.mock.calls[1][0]).toHaveLength(1);
    expect(Object.keys(get(assessments))).toHaveLength(101);
    expect(get(assessments)['eip155:1/erc20:0x0']).toStrictEqual({ prediction: prediction(), status: 'ready' });
  });

  it('should forward a transaction reference only when there is one', async () => {
    assess(ref([token('eip155:1/erc20:0x1', '0xabc'), token('eip155:1/erc20:0x2', '')]));
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledWith([
      { identifier: 'eip155:1/erc20:0x1', txReference: '0xabc' },
      { identifier: 'eip155:1/erc20:0x2' },
    ]);
  });

  it('should report unsupported tokens without inventing a score', async () => {
    predictSpam.mockResolvedValue({ 'eip155:1/erc20:0x1': null });

    const { assessments, status } = assess(ref([token('eip155:1/erc20:0x1')]));
    await flushPromises();

    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ status: 'unsupported' });
    expect(get(status)).toBe('ready');
  });

  it('should keep successful batches and report failed ones as unavailable', async () => {
    const page = Array.from({ length: 101 }, (_, index) => token(`eip155:1/erc20:0x${index}`));
    predictSpam
      .mockImplementationOnce(async (tokens: { identifier: string }[]) => Object.fromEntries(
        tokens.map(({ identifier }) => [identifier, prediction()]),
      ))
      .mockRejectedValueOnce(new Error('backend unavailable'));

    const { assessments, status } = assess(ref(page));
    await flushPromises();

    expect(get(assessments)['eip155:1/erc20:0x0']?.status).toBe('ready');
    expect(get(assessments)['eip155:1/erc20:0x100']).toStrictEqual({ status: 'unavailable' });
    expect(get(status)).toBe('unavailable');
  });

  it('should drop the previous page score before the next page resolves', async () => {
    const { promise: nextBatch, resolve: resolveNext } = deferred<Record<string, SpamPrediction | null>>();

    const page = ref([token('eip155:1/erc20:0xOld')]);
    const { assessments } = assess(page);
    await flushPromises();
    expect(get(assessments)['eip155:1/erc20:0xOld']?.status).toBe('ready');

    predictSpam.mockReturnValueOnce(nextBatch);
    set(page, [token('eip155:1/erc20:0xNew')]);

    expect(get(assessments)['eip155:1/erc20:0xOld']).toBeUndefined();
    expect(get(assessments)['eip155:1/erc20:0xNew']).toStrictEqual({ status: 'loading' });

    resolveNext({ 'eip155:1/erc20:0xNew': prediction(0.2, 0.5) });
    await flushPromises();

    expect(get(assessments)['eip155:1/erc20:0xNew']).toStrictEqual({ prediction: prediction(0.2, 0.5), status: 'ready' });
    expect(get(assessments)['eip155:1/erc20:0xOld']).toBeUndefined();
  });

  it('should clear scores and cache when the session ends and refetch for the next session', async () => {
    const page = ref([token('eip155:1/erc20:0x1')]);
    const { assessments, status } = assess(page);
    await flushPromises();

    const callsFirstSession = predictSpam.mock.calls.length;
    endSession();

    expect(get(assessments)).toStrictEqual({});
    expect(get(status)).toBe('idle');

    beginSession();
    await flushPromises();

    expect(predictSpam.mock.calls).toHaveLength(callsFirstSession + 1);
    expect(get(assessments)['eip155:1/erc20:0x1']?.status).toBe('ready');
  });

  it('should skip refetching and keep ready scores when the page array is replaced with identical entries', async () => {
    const firstPrediction = prediction(0.8, 0.5);
    predictSpam.mockResolvedValueOnce({ 'eip155:1/erc20:0x1': firstPrediction });
    const page = ref([token('eip155:1/erc20:0x1', '0xtx1')]);
    const { assessments, status } = assess(page);
    await flushPromises();

    set(page, [token('eip155:1/erc20:0x1', '0xtx1')]);

    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ prediction: firstPrediction, status: 'ready' });
    expect(get(status)).toBe('ready');
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledTimes(1);
  });

  it('should keep existing tokens ready and request only newly appended tokens on load more', async () => {
    const existingPrediction = prediction(0.2, 0.5);
    const addedPrediction = prediction(0.9, 0.5);
    predictSpam
      .mockResolvedValueOnce({ 'eip155:1/erc20:0x1': existingPrediction })
      .mockImplementationOnce(async () => ({ 'eip155:1/erc20:0x2': addedPrediction }));

    const page = ref([token('eip155:1/erc20:0x1')]);
    const { assessments, status } = assess(page);
    await flushPromises();

    set(page, [token('eip155:1/erc20:0x1'), token('eip155:1/erc20:0x2')]);

    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ prediction: existingPrediction, status: 'ready' });
    expect(get(assessments)['eip155:1/erc20:0x2']).toStrictEqual({ status: 'loading' });
    expect(get(status)).toBe('loading');

    await flushPromises();

    expect(predictSpam).toHaveBeenCalledTimes(2);
    expect(predictSpam.mock.calls[1][0]).toStrictEqual([{ identifier: 'eip155:1/erc20:0x2' }]);
    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ prediction: existingPrediction, status: 'ready' });
    expect(get(assessments)['eip155:1/erc20:0x2']).toStrictEqual({ prediction: addedPrediction, status: 'ready' });
    expect(get(status)).toBe('ready');
  });

  it('should re-request only tokens whose txReference changed while keeping unchanged tokens cached', async () => {
    const stablePrediction = prediction(0.1, 0.5);
    const updatedPrediction = prediction(0.85, 0.5);
    predictSpam
      .mockResolvedValueOnce({
        'eip155:1/erc20:0x1': stablePrediction,
        'eip155:1/erc20:0x2': prediction(0.3, 0.5),
      })
      .mockResolvedValueOnce({ 'eip155:1/erc20:0x2': updatedPrediction });

    const page = ref([
      token('eip155:1/erc20:0x1', '0xtx1'),
      token('eip155:1/erc20:0x2', '0xtx2'),
    ]);
    const { assessments } = assess(page);
    await flushPromises();

    set(page, [
      token('eip155:1/erc20:0x1', '0xtx1'),
      token('eip155:1/erc20:0x2', '0xtx2-updated'),
    ]);

    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ prediction: stablePrediction, status: 'ready' });
    expect(get(assessments)['eip155:1/erc20:0x2']).toStrictEqual({ status: 'loading' });

    await flushPromises();

    expect(predictSpam).toHaveBeenCalledTimes(2);
    expect(predictSpam.mock.calls[1][0]).toStrictEqual([{ identifier: 'eip155:1/erc20:0x2', txReference: '0xtx2-updated' }]);
    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ prediction: stablePrediction, status: 'ready' });
    expect(get(assessments)['eip155:1/erc20:0x2']).toStrictEqual({ prediction: updatedPrediction, status: 'ready' });
  });

  it('should drop removed tokens from assessments with zero network requests', async () => {
    const keptPrediction = prediction(0.4, 0.5);
    predictSpam.mockResolvedValueOnce({
      'eip155:1/erc20:0x1': keptPrediction,
      'eip155:1/erc20:0x2': prediction(0.9, 0.5),
    });

    const page = ref([
      token('eip155:1/erc20:0x1'),
      token('eip155:1/erc20:0x2'),
    ]);
    const { assessments, status } = assess(page);
    await flushPromises();

    set(page, [token('eip155:1/erc20:0x1')]);

    expect(predictSpam).toHaveBeenCalledTimes(1);
    expect(get(assessments)).toStrictEqual({
      'eip155:1/erc20:0x1': { prediction: keptPrediction, status: 'ready' },
    });
    expect(get(status)).toBe('ready');
  });

  it('should cache unsupported outcomes but retry unavailable tokens on subsequent changes', async () => {
    predictSpam
      .mockRejectedValueOnce(new Error('temporary failure'))
      .mockResolvedValueOnce({
        'eip155:1/erc20:0x1': prediction(0.7, 0.5),
        'eip155:1/erc20:0x2': null,
      });

    const page = ref([token('eip155:1/erc20:0x1')]);
    const { assessments, status } = assess(page);
    await flushPromises();
    expect(get(assessments)['eip155:1/erc20:0x1']).toStrictEqual({ status: 'unavailable' });

    set(page, [token('eip155:1/erc20:0x1'), token('eip155:1/erc20:0x2')]);
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledTimes(2);
    expect(predictSpam.mock.calls[1][0]).toStrictEqual([
      { identifier: 'eip155:1/erc20:0x1' },
      { identifier: 'eip155:1/erc20:0x2' },
    ]);
    expect(get(assessments)['eip155:1/erc20:0x2']).toStrictEqual({ status: 'unsupported' });

    set(page, [token('eip155:1/erc20:0x2')]);
    expect(predictSpam).toHaveBeenCalledTimes(2);
    expect(get(assessments)).toStrictEqual({ 'eip155:1/erc20:0x2': { status: 'unsupported' } });
    expect(get(status)).toBe('ready');
  });

  it('should not request anything for an empty page', async () => {
    const { assessments, status } = assess(ref([]));
    await flushPromises();

    expect(predictSpam).not.toHaveBeenCalled();
    expect(get(assessments)).toStrictEqual({});
    expect(get(status)).toBe('idle');
  });
});

describe('isErc20TokenIdentifier', () => {
  it.each([
    'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
    'eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  ])('should accept ERC-20 identifier %s', (identifier) => {
    expect(isErc20TokenIdentifier(identifier)).toBe(true);
  });

  it.each([
    null,
    undefined,
    '',
    'ETH',
    'BTC',
    'eip155:1/erc20:',
    'eip155:/erc20:0x123',
    'eip155:1/erc721:0x123',
    'eip155:1/erc1155:0x123',
    'solana/token:So11111111111111111111111111111111111111112',
  ])('should reject non-ERC-20 identifier %s', (identifier) => {
    expect(isErc20TokenIdentifier(identifier)).toBe(false);
  });
});
