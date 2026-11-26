import type { NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { assert, TimeFramePeriod, TimeFramePersist, timeframes, type TimeFrameSetting, TimeUnit } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import dayjs from 'dayjs';
import { computed, type ComputedRef, onMounted, type Ref, watch } from 'vue';
import { usePremium } from '@/modules/premium/use-premium';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { isPeriodAllowed } from '@/modules/settings/settings-utils';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseNetValueTimeframeOptions {
  /** The chart's zoom window, cleared whenever the timeframe changes. */
  readonly zoomRange: Ref<NetValueZoomRange | undefined>;
  /** Runs after a new timeframe is put in the session and before it is persisted, e.g. to reset the chart zoom. */
  readonly onTimeframeChange?: () => void;
}

interface UseNetValueTimeframeReturn {
  readonly timeframe: Readonly<Ref<SettingValue<'timeframe'>>>;
  readonly visibleTimeframes: Readonly<Ref<SettingValue<'visibleTimeframes'>>>;
  readonly timeframeData: ComputedRef<NetValueChartData>;
  readonly setTimeframe: (value: TimeFrameSetting) => Promise<void>;
}

/**
 * The net value graph's selected timeframe: the session setting, the chart data it selects, the
 * handler that switches it, and the guard that drops a premium-only period for non-premium users.
 */
export function useNetValueTimeframe(options: UseNetValueTimeframeOptions): UseNetValueTimeframeReturn {
  const { onTimeframeChange, zoomRange } = options;

  const settingsRepo = useSettingsRepo();
  const { getNetValue } = useStatisticsStore();
  const timeframe = useSetting('timeframe');
  const visibleTimeframes = useSetting('visibleTimeframes');
  const premium = usePremium();
  const { updateFrontendSetting } = useSettingsOperations();

  const allTimeframes = computed(() =>
    timeframes((unit, amount) => dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()),
  );

  const timeframeData = computed<NetValueChartData>(() => {
    const all = get(allTimeframes);
    const selection = get(timeframe);
    const startingDate = all[selection].startingDate();
    return getNetValue(startingDate);
  });

  async function setTimeframe(value: TimeFrameSetting): Promise<void> {
    assert(value !== TimeFramePersist.REMEMBER);
    settingsRepo.updateSession({ timeframe: value });
    onTimeframeChange?.();
    await updateFrontendSetting({ lastKnownTimeframe: value });
  }

  /**
   * Drops the zoom when the timeframe changes, so the header goes back to full-range numbers after
   * the user switches buttons. Watching the timeframe rather than the data leaves an active zoom
   * alone across routine balance refreshes.
   */
  function clearZoomForNewTimeframe(): void {
    set(zoomRange, undefined);
  }

  watch(timeframe, clearZoomForNewTimeframe);

  onMounted(() => {
    if (!get(premium) && !isPeriodAllowed(get(timeframe)))
      settingsRepo.updateSession({ timeframe: TimeFramePeriod.TWO_WEEKS });
  });

  return {
    setTimeframe,
    timeframe,
    timeframeData,
    visibleTimeframes,
  };
}
