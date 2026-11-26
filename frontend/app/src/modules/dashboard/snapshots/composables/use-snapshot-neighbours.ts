import type { BigNumber } from '@rotki/common';
import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { useRouter } from 'vue-router';

interface UseSnapshotNeighboursOptions {
  /** The timestamp, in seconds, of the snapshot on screen. */
  timestamp: MaybeRefOrGetter<number>;
  /** Every snapshot from the net-value series, in any order. */
  rows: MaybeRefOrGetter<SnapshotListRow[]>;
}

/** The net worth of the chronologically previous snapshot, for the summary's delta. */
interface PreviousSnapshot {
  value: BigNumber;
  timestamp: number;
}

interface UseSnapshotNeighboursReturn {
  /** Whether an older snapshot exists. */
  hasPrev: ComputedRef<boolean>;
  /** Whether a newer snapshot exists. */
  hasNext: ComputedRef<boolean>;
  /** The older neighbour's net worth, when there is one in the series. */
  previous: ComputedRef<PreviousSnapshot | undefined>;
  /** Opens the older or newer neighbour; does nothing at either end. */
  navigate: (direction: 'prev' | 'next') => void;
}

/** Orders the snapshots around the one on screen, for prev/next navigation and the delta. */
export function useSnapshotNeighbours(options: UseSnapshotNeighboursOptions): UseSnapshotNeighboursReturn {
  const { rows, timestamp } = options;
  const router = useRouter();

  /** Snapshot timestamps oldest-first, used for prev/next navigation + the delta. */
  const orderedTimestamps = computed<number[]>(() => toValue(rows).map(row => row.timestamp).sort((a, b) => a - b));
  const currentIndex = computed<number>(() => get(orderedTimestamps).indexOf(toValue(timestamp)));
  const hasPrev = computed<boolean>(() => get(currentIndex) > 0);
  const hasNext = computed<boolean>(() => {
    const index = get(currentIndex);
    return index > -1 && index < get(orderedTimestamps).length - 1;
  });

  const previousTimestamp = computed<number | undefined>(() => {
    const index = get(currentIndex);
    return index > 0 ? get(orderedTimestamps)[index - 1] : undefined;
  });

  const previous = computed<PreviousSnapshot | undefined>(() => {
    const ts = get(previousTimestamp);
    if (ts === undefined)
      return undefined;
    const value = toValue(rows).find(row => row.timestamp === ts)?.usdValue;
    return value !== undefined ? { timestamp: ts, value } : undefined;
  });

  function navigate(direction: 'prev' | 'next'): void {
    const target = get(orderedTimestamps)[get(currentIndex) + (direction === 'next' ? 1 : -1)];
    if (target !== undefined)
      startPromise(router.push(`/statistics/snapshots/${target}`));
  }

  return { hasNext, hasPrev, navigate, previous };
}
