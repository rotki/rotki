<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { type AddressProgress, AddressStatus, AddressStep, AddressSubtype } from '../types';

const props = withDefaults(defineProps<{
  address: AddressProgress;
  chain: string;
  compact?: boolean;
}>(), {
  compact: false,
});

const { t } = useI18n({ useScope: 'global' });

const isComplete = computed<boolean>(() => props.address.status === AddressStatus.COMPLETE);
const isQuerying = computed<boolean>(() => props.address.status === AddressStatus.QUERYING);
const isDecoding = computed<boolean>(() => props.address.status === AddressStatus.DECODING);

const statusIcon = computed<string>(() => {
  if (get(isComplete))
    return 'lu-check';
  if (get(isQuerying) || get(isDecoding))
    return 'lu-loader-circle';
  return 'lu-circle';
});

const statusColor = computed<string>(() => {
  if (get(isComplete))
    return 'text-rui-success';
  if (get(isQuerying) || get(isDecoding))
    return 'text-rui-primary';
  return 'text-rui-text-disabled';
});

const statusText = computed<string>(() => {
  if (get(isComplete))
    return t('sync_progress.status.complete');

  if (get(isDecoding))
    return t('sync_progress.status.decoding');

  if (get(isQuerying)) {
    switch (props.address.step) {
      case AddressStep.TRANSACTIONS:
        return t('sync_progress.status.querying_transactions');
      case AddressStep.INTERNAL:
        return t('sync_progress.status.querying_internal');
      case AddressStep.TOKENS:
        return t('sync_progress.status.querying_tokens');
      default:
        return t('sync_progress.status.querying');
    }
  }

  return t('sync_progress.status.pending');
});

const hasPeriod = computed<boolean>(() =>
  get(isQuerying) && !!props.address.period && props.address.subtype !== AddressSubtype.BITCOIN,
);

// Current position is period[1], show "Beginning" if current is 0 or equals start (hasn't progressed)
const showBeginning = computed<boolean>(() => {
  const period = props.address.period;
  if (!period)
    return false;
  return period[1] === 0 || period[1] === period[0];
});

const hasPeriodProgress = computed<boolean>(() =>
  get(isQuerying) && props.address.periodProgress !== undefined && props.address.subtype !== AddressSubtype.BITCOIN,
);
</script>

<template>
  <div
    class="flex items-center gap-2 px-2 rounded hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700"
    :class="[compact ? 'py-0.5' : 'py-1', { 'animate-pulse bg-rui-primary/5': isQuerying || isDecoding }]"
  >
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 text-rui-text">
        <HashLink
          :text="address.address"
          :location="chain"
          :class="compact ? 'text-xs' : 'text-sm'"
        />

        <template v-if="hasPeriodProgress && !compact">
          <div class="flex-1 max-w-[80px]">
            <RuiProgress
              :value="address.periodProgress"
              color="primary"
              size="sm"
              rounded
            />
          </div>
          <span class="text-[10px] text-rui-text-secondary tabular-nums">
            {{ t('percentage_display.value', { value: address.periodProgress }) }}
          </span>
        </template>
      </div>

      <div
        v-if="hasPeriod && address.period && !compact"
        class="text-xs text-rui-text-secondary flex items-center gap-1"
      >
        <span v-if="showBeginning">
          {{ t('sync_progress.period.beginning') }}
        </span>
        <DateDisplay
          v-else
          :timestamp="address.period[1]"
          date-only
        />
        <RuiIcon
          name="lu-arrow-right"
          size="12"
        />
        <DateDisplay
          :timestamp="address.originalPeriodEnd ?? address.period[1]"
          date-only
        />
      </div>
    </div>

    <span
      class="text-rui-text-secondary whitespace-nowrap"
      :class="compact ? 'text-[10px]' : 'text-xs'"
    >
      {{ statusText }}
    </span>

    <RuiIcon
      :name="statusIcon"
      :class="[statusColor, { 'animate-spin': isQuerying || isDecoding }]"
      :size="compact ? 12 : 16"
    />
  </div>
</template>
