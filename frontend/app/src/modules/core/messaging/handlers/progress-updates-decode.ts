import type { EvmUnDecodedTransactionsData, ProtocolCacheUpdatesData } from '@/modules/core/messaging/types/status-types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { decodeActivity, decodeActivityId, type DecodeSubject } from '@/modules/history/events/tx/decode.activity';
import { protocolCacheActivity, withProtocolCacheFrame } from '@/modules/history/protocol-cache.activity';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { peekActivityDetail, publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface DecodeProgressHandlers {
  /** Routes a protocol-cache frame to the cache refresh or the decode that is filling it. */
  handleProtocolCacheUpdates: (data: ProtocolCacheUpdatesData) => void;
  /** Records a chain's undecoded count and reports it onto the chain-wide decode activity. */
  handleUndecodedTransactions: (data: EvmUnDecodedTransactionsData) => void;
}

/**
 * The progress-update handlers for transaction decoding: the undecoded-transactions counts and the
 * protocol-cache frames a decoder sends while it fills a cache.
 */
export function createDecodeProgressHandlers(): DecodeProgressHandlers {
  const { setUndecodedTransactionsStatus } = useDecodingStatusStore();
  const { reportProgress, statusOf } = useTaskOrchestrator();
  const { matchChain } = useSupportedChains();

  /**
   * Report a chain's decode progress onto the chain-wide decode activity.
   *
   * Two exact ids rather than a prefix over the chain: a prefix would also match
   * `targetedDecodeActivityId`, whose denominator is the transactions that request named, not the
   * chain's undecoded count. Only one of the two can be running for a chain, and `reportProgress`
   * ignores an id that is not, so the pair is a single report either way.
   *
   * The chain is canonicalised first. The decoder reports `ChainID.to_name()` ('ethereum') while
   * the activity carries the chain id its flow submitted ('eth'), so the raw value matches nothing
   * and the decode would sit at zero for the whole run.
   */
  function reportDecodeProgress(data: { chain: string; processed: number; total: number }): void {
    const chain = matchChain(data.chain) ?? data.chain.toLowerCase();
    const steps = { current: data.processed, total: data.total };
    reportProgress(decodeActivityId(chain, false), steps);
    reportProgress(decodeActivityId(chain, true), steps);
  }

  /**
   * The decode variant currently running for a chain, if either is.
   *
   * A chain's cached and forced decodes are separate activities, and only one of the pair can be
   * live. Publishing to both instead would leave an entry against an id with no record, which
   * nothing ever drops: the channel is cleaned up by the orchestrator, and it can only clean up
   * what it has a record for.
   */
  function liveDecodeSubject(chain: string): DecodeSubject | undefined {
    return [{ chain, ignoreCache: false }, { chain, ignoreCache: true }]
      .find(subject => statusOf(decodeActivity.kind, ...decodeActivity.partsOf(subject)).running);
  }

  /**
   * Attach the protocol-cache rows to whatever work is filling them.
   *
   * Two producers send the same frames: the user's cache refresh, which has an activity of its own,
   * and decoding, which fills a cache when a decoder reaches a log that needs one. Each frame is
   * folded into the rows that activity already holds, so the rows are the set this run has touched
   * rather than the single pair this frame carries; a run starts empty because the orchestrator
   * drops an activity's detail when it is submitted or rerun.
   *
   * Published only against a live record, and nothing at all when neither is running. That covers
   * every frame today that arrives outside both, and is what the panel already shows for them. The
   * same check keeps a cancelled run's rows as they were when it stopped.
   */
  function handleProtocolCacheUpdates(data: ProtocolCacheUpdatesData): void {
    if (statusOf(protocolCacheActivity.kind).running) {
      const rows = peekActivityDetail(protocolCacheActivity, undefined)?.protocols ?? [];
      publishActivityDetail(protocolCacheActivity, undefined, { protocols: withProtocolCacheFrame(rows, data) });
    }

    const decoding = liveDecodeSubject(matchChain(data.chain) ?? data.chain.toLowerCase());
    if (decoding !== undefined) {
      const rows = peekActivityDetail(decodeActivity, decoding)?.protocols ?? [];
      publishActivityDetail(decodeActivity, decoding, { protocols: withProtocolCacheFrame(rows, data) });
    }
  }

  function handleUndecodedTransactions(data: EvmUnDecodedTransactionsData): void {
    setUndecodedTransactionsStatus(data);
    reportDecodeProgress(data);
  }

  return {
    handleProtocolCacheUpdates,
    handleUndecodedTransactions,
  };
}
