<script setup lang="ts">
import { type BigNumber, type NetValue, Zero } from '@rotki/common';
import VChart from 'vue-echarts';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import NewGraphTooltipWrapper from '@/components/graphs/NewGraphTooltipWrapper.vue';
import { useNetValueChartConfig } from '@/modules/dashboard/graph/use-net-value-chart-config';
import { useNetValueEventHandlers } from '@/modules/dashboard/graph/use-net-value-event-handlers';
import { useGeneralSettingsStore } from '@/store/settings/general';

const props = defineProps<{
  chartData: NetValue;
}>();

const { chartData } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const chartContainer = ref<HTMLElement>();
const chartInstance = ref<InstanceType<typeof VChart>>();

const selectedTimestamp = ref<number>(0);
const selectedBalance = ref<BigNumber>(Zero);
const showExportSnapshotDialog = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { isDark } = useRotkiTheme();

const { chartOption } = useNetValueChartConfig(chartData);
const { setupChartEventHandlers, setupZoomToolHandler, tooltipData } = useNetValueEventHandlers({
  chartContainer,
  chartData,
  chartInstance,
  onHover: (timestamp: number, balance: BigNumber) => {
    set(selectedTimestamp, timestamp);
    set(selectedBalance, balance);
    set(showExportSnapshotDialog, true);
  },
});

watchImmediate(isDark, () => {
  nextTick(setupChartEventHandlers);
});

watchImmediate(chartOption, () => {
  setupZoomToolHandler();
});
</script>

<template>
  <div
    ref="chartContainer"
    class="relative w-full h-full"
  >
    <VChart
      ref="chartInstance"
      class="flex-grow w-full h-[18rem] [&>div:last-child]:!hidden"
      :option="chartOption"
      autoresize
    />
  </div>

  <NewGraphTooltipWrapper :tooltip-option="tooltipData">
    <div class="text-rui-text-secondary text-xs mb-1">
      <DateDisplay
        v-if="!tooltipData.currentBalance"
        :timestamp="tooltipData.timestamp"
        milliseconds
      />
      <template v-else>
        {{ t('net_worth_chart.current_balance') }}
      </template>
    </div>
    <AmountDisplay
      class="font-bold"
      force-currency
      show-currency="symbol"
      :value="tooltipData.value"
      :fiat-currency="currencySymbol"
    />
  </NewGraphTooltipWrapper>

  <ExportSnapshotDialog
    v-if="selectedTimestamp && selectedBalance"
    v-model="showExportSnapshotDialog"
    :timestamp="selectedTimestamp"
    :balance="selectedBalance"
  />
</template>
