import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { blockDecodeActivityId, targetedDecodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useEventRedecodeStatus } from './use-event-redecode-status';

const mocks = vi.hoisted(() => ({
  statusOf: vi.fn(),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChain: vi.fn((location: string) => (location === 'ethereum' ? 'eth' : location)),
  })),
}));

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn(() => ({
    statusOf: mocks.statusOf,
    version: ref(0),
  })),
}));

function evmEvent(txRef: string): HistoryEventEntry {
  return createMock<HistoryEventEntry>({
    entryType: HistoryEventEntryType.EVM_EVENT,
    location: 'ethereum',
    txRef,
  });
}

function blockEvent(blockNumber: number): HistoryEventEntry {
  return createMock<HistoryEventEntry>({
    blockNumber,
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    location: 'ethereum',
  });
}

/** The id the composable asked about, rebuilt from the arguments `statusOf` received. */
function queriedId(): string {
  const [kind, ...parts] = mocks.statusOf.mock.calls[0];
  return makeActivityId(kind, ...parts);
}

describe('useEventRedecodeStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.statusOf.mockReturnValue({ active: false, everCompleted: false, pending: false, running: false });
  });

  it('should ask about the same activity id the targeted redecode submits', () => {
    const status = useEventRedecodeStatus(() => evmEvent('0xabc'), () => []);
    get(status);

    expect(mocks.statusOf).toHaveBeenCalledWith(ActivityKind.TX_DECODING, 'eth', 'pull', '0xabc');
    expect(queriedId()).toBe(targetedDecodeActivityId('eth', ['0xabc']));
  });

  it('should ask about the block decode id for a block event', () => {
    const status = useEventRedecodeStatus(() => blockEvent(21_000_000), () => []);
    get(status);

    expect(queriedId()).toBe(blockDecodeActivityId([21_000_000]));
  });

  it('should report the orchestrator liveness for that activity', () => {
    mocks.statusOf.mockReturnValue({ active: true, everCompleted: false, pending: false, running: true });

    const status = useEventRedecodeStatus(() => evmEvent('0xabc'), () => []);

    expect(get(status)).toBe(true);
  });

  it('should fall back to the first decodable child when the group header is not decodable', () => {
    const header = createMock<HistoryEventEntry>({
      entryType: HistoryEventEntryType.HISTORY_EVENT,
      location: 'ethereum',
    });

    const status = useEventRedecodeStatus(() => header, () => [evmEvent('0xdef')]);
    get(status);

    expect(queriedId()).toBe(targetedDecodeActivityId('eth', ['0xdef']));
  });

  it('should stay inactive for an event that cannot be redecoded', () => {
    const header = createMock<HistoryEventEntry>({
      entryType: HistoryEventEntryType.HISTORY_EVENT,
      location: 'kraken',
    });

    const status = useEventRedecodeStatus(() => header, () => []);

    expect(get(status)).toBe(false);
    expect(mocks.statusOf).not.toHaveBeenCalled();
  });

  it('should track the event it is given rather than the one it started with', () => {
    // A getter over a plain ref of the tx ref, rather than a ref holding the mock itself: the mock
    // is a Proxy and Vue's `toRaw` recurses forever on one placed in reactive state.
    const txRef = ref<string>('0xabc');
    const status = useEventRedecodeStatus(() => evmEvent(get(txRef)), () => []);
    get(status);

    set(txRef, '0xfeed');
    get(status);

    const [kind, ...parts] = mocks.statusOf.mock.calls[1];
    expect(makeActivityId(kind, ...parts)).toBe(targetedDecodeActivityId('eth', ['0xfeed']));
  });
});
