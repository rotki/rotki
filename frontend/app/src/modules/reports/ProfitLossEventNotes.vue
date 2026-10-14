<script setup lang="ts">
import type { ProfitLossEvent } from '@/modules/reports/report-types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import { isTransactionEvent } from '@/modules/reports/report-utils';

const { event } = defineProps<{
  event: ProfitLossEvent;
}>();

const { getChain } = useSupportedChains();
</script>

<template>
  <div
    v-if="event.notes"
    class="py-1 line-clamp-2"
    :title="event.notes"
  >
    <HistoryEventNote
      v-if="isTransactionEvent(event)"
      :notes="event.notes"
      :context="{
        amount: event.taxableAmount.isZero() ? event.freeAmount : event.taxableAmount,
        asset: event.assetIdentifier,
      }"
      :chain="getChain(event.location)"
    />
    <HistoryEventNote
      v-else
      :notes="event.notes"
      :context="{ asset: event.assetIdentifier }"
    />
  </div>
  <div
    v-else
    class="py-1"
  >
    -
  </div>
</template>
