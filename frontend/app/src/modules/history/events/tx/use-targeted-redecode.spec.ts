import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { createMock } from '@test/utils/create-mock';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { blockDecodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { targetedRedecodeFlow } from '@/modules/history/events/tx/targeted-redecode.flow';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTargetedRedecode } from './use-targeted-redecode';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  pullAndRecodeEthBlockEventRequest: vi.fn(),
  pullAndRecodeTransactionRequest: vi.fn(),
  runTaskResult: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    reportProgress: vi.fn(),
    runTaskResult: mocks.runTaskResult,
    submitTask: mocks.submitTask,
  })),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => createMock<ReturnType<typeof useHistoryEventsApi>>({
    pullAndRecodeEthBlockEventRequest: mocks.pullAndRecodeEthBlockEventRequest,
    pullAndRecodeTransactionRequest: mocks.pullAndRecodeTransactionRequest,
  })),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: vi.fn(() => ({
    resetUndecodedTransactionsStatus: vi.fn(),
    updateUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChain: vi.fn((chain: string) => chain),
    getChainName: vi.fn((chain: string) => chain),
    isEvmLikeChains: vi.fn(() => false),
    isSolanaChains: vi.fn(() => false),
  })),
}));

describe('useTargetedRedecode', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  describe('redecodeTargeted', () => {
    it('should submit a named umbrella with the block decode as its child', async () => {
      const { redecodeTargeted } = useTargetedRedecode();
      await redecodeTargeted({ blockNumbers: [1, 2] });

      const [umbrella, child] = mocks.submitTask.mock.calls.map(call => call[0]);
      expect(umbrella).toMatchObject({
        id: targetedRedecodeFlow.id({ blocks: [1, 2], byChain: [] }),
        kind: ActivityKind.REDECODE,
        resets: true,
      });
      expect(child).toMatchObject({
        id: blockDecodeActivityId([1, 2]),
        kind: ActivityKind.ETH_BLOCK_DECODING,
        parent: umbrella.id,
        rerunnable: false,
      });
    });

    it('should key the block decode id by its block set so a request for different blocks cannot dedup onto an in-flight one, order-insensitively', async () => {
      expect(blockDecodeActivityId([1, 2])).not.toBe(blockDecodeActivityId([99]));
      expect(blockDecodeActivityId([2, 1])).toBe(blockDecodeActivityId([1, 2]));
    });

    it('should do nothing when the request names neither transactions nor blocks', async () => {
      const { redecodeTargeted } = useTargetedRedecode();
      await redecodeTargeted({});

      expect(mocks.submitTask).not.toHaveBeenCalled();
    });
  });

  /**
   * These three subtitles were built by hand and so bypassed `activityLabelFor` entirely, which is
   * why a sweep that grepped for that call missed them. They rendered a bare count ("Ethereum · 2"),
   * a full 66-character transaction hash, and a bare block number — none of which say what the row
   * is doing. Asserting the {@link TranslatableText} shape rather than a rendered string keeps this
   * honest: a hand-built string cannot satisfy it.
   */
  describe('subtitles', () => {
    const txHash = '0x1234567890123456789012345678901234567890123456789012345678901234';

    async function subtitleOf(run: () => Promise<void>): Promise<any> {
      await run();
      return mocks.submitTask.mock.calls.at(-1)?.[0].subtitle;
    }

    it('should name a single transaction with a truncated hash, not the bare hash', async () => {
      const { pullAndDecodeTransactionsRaw } = useTargetedRedecode();
      const subtitle = await subtitleOf(async () => {
        await pullAndDecodeTransactionsRaw({ chain: 'ethereum', txRefs: [txHash] }).catch(() => {});
      });

      expect(subtitle.key).toBe('task_center.activity.tx_decoding.single');
      expect(subtitle.params.chain).toBe('ethereum');
      expect(subtitle.params.tx).not.toBe(txHash);
      expect(subtitle.params.tx.length).toBeLessThan(txHash.length);
    });

    it('should describe a batch of transactions by count, pluralised', async () => {
      const { pullAndDecodeTransactionsRaw } = useTargetedRedecode();
      const subtitle = await subtitleOf(async () => {
        await pullAndDecodeTransactionsRaw({ chain: 'ethereum', txRefs: [txHash, '0xabc'] }).catch(() => {});
      });

      expect(subtitle.key).toBe('task_center.activity.tx_decoding.batch');
      expect(subtitle.params).toMatchObject({ chain: 'ethereum', count: 2 });
      // Without the plural argument the message renders its singular half for every count.
      expect(subtitle.plural).toBe(2);
    });

    it('should name a single block, not print the number on its own', async () => {
      const { redecodeTargeted } = useTargetedRedecode();
      const subtitle = await subtitleOf(async () => redecodeTargeted({ blockNumbers: [25644057] }));

      expect(subtitle.key).toBe('task_center.activity.eth_block_decoding.single');
      expect(subtitle.params).toMatchObject({ block: 25644057 });
    });

    it('should describe a batch of blocks by count, pluralised', async () => {
      const { redecodeTargeted } = useTargetedRedecode();
      const subtitle = await subtitleOf(async () => redecodeTargeted({ blockNumbers: [1, 2, 3] }));

      expect(subtitle.key).toBe('task_center.activity.eth_block_decoding.batch');
      expect(subtitle.params).toMatchObject({ count: 3 });
      expect(subtitle.plural).toBe(3);
    });

    it('should settle the umbrella when a child fails, rather than surface the first failure', async () => {
      mocks.submitTask.mockImplementation(async (spec: { kind: ActivityKind; run: () => Promise<unknown> }) => {
        if (spec.kind === ActivityKind.REDECODE)
          return spec.run();
        throw new Error('child failed');
      });

      const { redecodeTargeted } = useTargetedRedecode();

      await expect(redecodeTargeted({ blockNumbers: [1, 2] })).resolves.toBeUndefined();
    });
  });

  describe('pullAndDecodeTransactionsRaw', () => {
    it('should throw on an actionable failure', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      const { pullAndDecodeTransactionsRaw } = useTargetedRedecode();
      await expect(pullAndDecodeTransactionsRaw({ chain: 'ethereum', txRefs: ['0x1'] }))
        .rejects
        .toThrow('boom');
    });

    it('should throw when the backend reports nothing decoded', async () => {
      mocks.runTaskResult.mockResolvedValue(ok(false));
      mocks.submitTask.mockImplementation(runSpecWith(mocks.runTaskResult));

      const { pullAndDecodeTransactionsRaw } = useTargetedRedecode();
      await expect(pullAndDecodeTransactionsRaw({ chain: 'ethereum', txRefs: ['0x1'] }))
        .rejects
        .toThrow();
    });

    it('should resolve when the backend decodes', async () => {
      mocks.runTaskResult.mockResolvedValue(ok(true));
      mocks.submitTask.mockImplementation(runSpecWith(mocks.runTaskResult));

      const { pullAndDecodeTransactionsRaw } = useTargetedRedecode();
      await expect(pullAndDecodeTransactionsRaw({ chain: 'ethereum', txRefs: ['0x1'] }))
        .resolves
        .toBeUndefined();
    });
  });
});
