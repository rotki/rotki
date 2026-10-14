<script setup lang="ts">
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import ProfitLossEventLocation from '@/modules/reports/ProfitLossEventLocation.vue';

const { type, location } = defineProps<{
  type: string;
  location: string;
}>();

const { getAccountingEventTypeData } = useHistoryEventMappings();

const data = getAccountingEventTypeData(() => type);
</script>

<template>
  <div class="flex items-center justify-center gap-3">
    <RuiTooltip
      v-if="data?.icon"
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <span
          class="inline-flex"
          :aria-label="data.label"
          data-testid="pnl-event-type"
        >
          <RuiIcon
            :name="data.icon"
            color="secondary"
            size="20"
          />
        </span>
      </template>
      {{ data.label }}
    </RuiTooltip>
    <span
      v-else
      class="whitespace-nowrap"
      data-testid="pnl-event-type"
    >
      {{ data?.label }}
    </span>
    <ProfitLossEventLocation :location="location" />
  </div>
</template>
