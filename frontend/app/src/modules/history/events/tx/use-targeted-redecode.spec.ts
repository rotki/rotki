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
  useHistoryEventsApi: vi.fn(() => ({
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
      // The child is gated by the umbrella, so the request reads as one named flow rather than a
      // bare decode with nothing saying what was asked for.
      expect(child).toMatchObject({
        id: blockDecodeActivityId([1, 2]),
        kind: ActivityKind.ETH_BLOCK_DECODING,
        parent: umbrella.id,
        rerunnable: false,
      });
    });

    it('should keep two different block requests apart', async () => {
      // The regression this guards: the id was a bare `ETH_BLOCK_DECODING` singleton, so a second
      // request for different blocks deduped onto the first and was handed its promise — its blocks
      // were never decoded.
      expect(blockDecodeActivityId([1, 2])).not.toBe(blockDecodeActivityId([99]));
      expect(blockDecodeActivityId([2, 1])).toBe(blockDecodeActivityId([1, 2]));
    });

    it('should do nothing when the request names neither transactions nor blocks', async () => {
      const { redecodeTargeted } = useTargetedRedecode();
      await redecodeTargeted({});

      expect(mocks.submitTask).not.toHaveBeenCalled();
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
      // run executes but the backend returns false → no decode happened
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
