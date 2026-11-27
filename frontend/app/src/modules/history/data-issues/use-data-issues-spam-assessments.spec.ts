import type { SpamPrediction, SpamPredictionResponse, SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, ref } from 'vue';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { toDataIssueSpamTokens, useDataIssuesSpamAssessments } from '@/modules/history/data-issues/use-data-issues-spam-assessments';

const { predictSpam, trustedAssets } = await vi.hoisted(async () => {
  const { ref: vueRef } = await import('vue');
  return {
    predictSpam: vi.fn<(tokens: SpamPredictionToken[]) => Promise<SpamPredictionResponse>>(),
    trustedAssets: vueRef<Set<string>>(new Set()),
  };
});

vi.mock(import('@/modules/assets/api/use-asset-spam-prediction-api'), async importOriginal => ({
  ...await importOriginal(),
  useAssetSpamPredictionApi: (): { predictSpam: typeof predictSpam } => ({ predictSpam }),
}));

vi.mock('@/modules/assets/spam/use-spam-token-trust', () => ({
  useSpamTokenTrust: (): { isTrustedForSpamDisplay: (asset?: string | null) => boolean } => ({
    isTrustedForSpamDisplay: (asset?: string | null): boolean => Boolean(asset && trustedAssets.value.has(asset)),
  }),
}));

const TOKEN_A = 'eip155:1/erc20:0x1111111111111111111111111111111111111111';
const TOKEN_B = 'eip155:137/erc20:0x2222222222222222222222222222222222222222';
const TX_HASH = `0x${'ab'.repeat(32)}`;
const RAW_HASH = 'cd'.repeat(32);

const FLAGGED_PREDICTION: SpamPrediction = {
  flagged: true,
  modelReasons: [],
  observedSignals: [{ code: 'url', field: 'name' }],
  spamProbability: 0.91,
  threshold: 0.5,
};

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: TOKEN_A,
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
    ...overrides,
  };
}

describe('toDataIssueSpamTokens', () => {
  it('should keep only ERC-20 issues and extract EVM transaction hashes from groupIdentifier or payload', () => {
    const tokens = toDataIssueSpamTokens([
      createIssue({ asset: 'ETH', id: 1 }),
      createIssue({ asset: null, id: 2 }),
      createIssue({ asset: 'eip155:1/erc721:0x3333', id: 3 }),
      createIssue({ asset: TOKEN_A, groupIdentifier: `1${TX_HASH}`, id: 4 }),
      createIssue({ asset: TOKEN_B, groupIdentifier: 'non-hash-group', id: 5, payload: { txRef: RAW_HASH } }),
    ]);

    expect(tokens).toStrictEqual([
      { identifier: TOKEN_A, txReference: TX_HASH },
      { identifier: TOKEN_B, txReference: RAW_HASH },
    ]);
  });

  it('should deduplicate repeated tokens and prefer an entry carrying a transaction hash', () => {
    const tokens = toDataIssueSpamTokens([
      createIssue({ asset: TOKEN_A, groupIdentifier: null, id: 1 }),
      createIssue({ asset: TOKEN_A, id: 2, payload: { groupIdentifier: `137${TX_HASH}` } }),
      createIssue({ asset: TOKEN_A, groupIdentifier: null, id: 3 }),
    ]);

    expect(tokens).toStrictEqual([{ identifier: TOKEN_A, txReference: TX_HASH }]);
  });
});

describe('useDataIssuesSpamAssessments', () => {
  let scopes: EffectScope[] = [];

  beforeEach(() => {
    beginSession();
    predictSpam.mockReset();
    trustedAssets.value = new Set();
  });

  afterEach(() => {
    scopes.forEach(scope => scope.stop());
    scopes = [];
    endSession();
  });

  it('should assess ERC-20 issues and leave non-ERC-20 or missing assets without an estimate', async () => {
    predictSpam.mockResolvedValueOnce({ [TOKEN_A]: FLAGGED_PREDICTION });
    const issues = ref<DataIssue[]>([
      createIssue({ asset: TOKEN_A, groupIdentifier: `1${TX_HASH}`, id: 1 }),
      createIssue({ asset: 'ETH', id: 2 }),
      createIssue({ asset: null, id: 3 }),
    ]);

    const scope = effectScope();
    scopes.push(scope);
    const { getSpamAssessment, status } = scope.run(() => useDataIssuesSpamAssessments(issues))!;
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledExactlyOnceWith([{ identifier: TOKEN_A, txReference: TX_HASH }]);
    expect(status.value).toBe('ready');
    expect(getSpamAssessment(TOKEN_A)).toStrictEqual({ prediction: FLAGGED_PREDICTION, status: 'ready' });
    expect(getSpamAssessment('ETH')).toBeUndefined();
    expect(getSpamAssessment(null)).toBeUndefined();
  });

  it('should skip trusted tokens, hide assessments if trust arrives later, and expose unavailable status', async () => {
    trustedAssets.value = new Set([TOKEN_A]);
    predictSpam.mockRejectedValueOnce(new Error('colibri offline'));
    const issues = ref<DataIssue[]>([
      createIssue({ asset: TOKEN_A, id: 1 }),
      createIssue({ asset: TOKEN_B, id: 2 }),
    ]);

    const scope = effectScope();
    scopes.push(scope);
    const { assessments, getSpamAssessment, status } = scope.run(() => useDataIssuesSpamAssessments(issues))!;
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledExactlyOnceWith([{ identifier: TOKEN_B }]);
    expect(status.value).toBe('unavailable');
    expect(getSpamAssessment(TOKEN_A)).toBeUndefined();
    expect(getSpamAssessment(TOKEN_B)).toStrictEqual({ status: 'unavailable' });

    trustedAssets.value = new Set([TOKEN_A, TOKEN_B]);
    await flushPromises();

    expect(assessments.value).toStrictEqual({});
    expect(getSpamAssessment(TOKEN_B)).toBeUndefined();
  });
});
