<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import AccountingOverlayToggle from '@/modules/history/balances/AccountingOverlayToggle.vue';
import BalanceDivergenceToggle from '@/modules/history/balances/BalanceDivergenceToggle.vue';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import HistoryEventsFiltersChips from '@/modules/history/events/HistoryEventsFiltersChips.vue';

const overlayMode = defineModel<OverlayMode>('overlayMode', { default: OverlayMode.NONE });

const { duplicateHandlingStatus, groupIdentifiers, overlayAvailable } = defineProps<{
  /** Group identifiers the URL pins the table to. */
  groupIdentifiers?: string[];
  /** Duplicate handling filter the URL pins. */
  duplicateHandlingStatus?: DuplicateHandlingStatus;
  /** Whether an accounting overlay can be shown for the current events. */
  overlayAvailable: boolean;
}>();

const emit = defineEmits<{
  /** The chips changed what is loaded, so the events need fetching again. */
  refresh: [];
}>();
</script>

<template>
  <div class="flex flex-wrap items-start gap-2 px-3 py-2 empty:hidden">
    <HistoryEventsFiltersChips
      class="mr-auto"
      :group-identifiers="groupIdentifiers"
      :duplicate-handling-status="duplicateHandlingStatus"
      @refresh="emit('refresh')"
    />
    <AccountingOverlayToggle
      v-if="overlayAvailable"
      v-model="overlayMode"
      class="ml-auto"
    />
    <BalanceDivergenceToggle v-if="overlayAvailable" />
  </div>
</template>
