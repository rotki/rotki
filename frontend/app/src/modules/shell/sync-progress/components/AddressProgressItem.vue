<script setup lang="ts">
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { type AddressProgress, AddressStatus, AddressStep } from '../types';

const { address } = defineProps<{
  address: AddressProgress;
  chain: string;
  compact?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const isComplete = computed<boolean>(() => address.status === AddressStatus.COMPLETE);
const isQuerying = computed<boolean>(() => address.status === AddressStatus.QUERYING);
const isDecoding = computed<boolean>(() => address.status === AddressStatus.DECODING);
const isCancelled = computed<boolean>(() => address.status === AddressStatus.CANCELLED);
/** Its own branch, so a failure does not fall through to the neutral fallback and read as pending. */
const isFailed = computed<boolean>(() => address.status === AddressStatus.FAILED);

const statusIcon = computed<string>(() => {
  if (get(isComplete))
    return 'lu-check';
  if (get(isFailed) || get(isCancelled))
    return 'lu-circle-alert';
  if (get(isQuerying) || get(isDecoding))
    return 'lu-loader-circle';
  return 'lu-circle';
});

const statusColor = computed<string>(() => {
  if (get(isComplete))
    return 'text-rui-success';
  if (get(isFailed))
    return 'text-rui-error';
  if (get(isCancelled))
    return 'text-rui-warning';
  if (get(isQuerying) || get(isDecoding))
    return 'text-rui-primary';
  return 'text-rui-text-disabled';
});

const statusText = computed<string>(() => {
  if (get(isComplete))
    return t('sync_progress.status.complete');

  if (get(isFailed))
    return t('sync_progress.status.failed');

  if (get(isCancelled))
    return t('sync_progress.status.cancelled');

  if (get(isDecoding))
    return t('sync_progress.status.decoding');

  if (get(isQuerying)) {
    switch (address.step) {
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

/**
 * Whether to render a range for this address.
 *
 * @remarks
 * Keyed on the period itself rather than on the subtype, so a chain gets a bar as soon as it sends
 * one and nothing here has to be taught which subtypes carry periods.
 */
const hasPeriod = computed<boolean>(() => get(isQuerying) && !!address.period);

// Current position is period[1], show "Beginning" if current is 0 or equals start (hasn't progressed)
const showBeginning = computed<boolean>(() => {
  const period = address.period;
  if (!period)
    return false;
  return period[1] === 0 || period[1] === period[0];
});

const hasPeriodProgress = computed<boolean>(() =>
  get(isQuerying) && address.periodProgress !== undefined,
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
