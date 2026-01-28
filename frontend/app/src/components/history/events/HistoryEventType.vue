<script setup lang="ts">
import type { Blockchain } from '@rotki/common';
import type { RuiIcons } from '@rotki/ui-library';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import HistoryEventAccount from '@/components/history/events/HistoryEventAccount.vue';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import HistoryEventTypeCounterparty from '@/components/history/events/HistoryEventTypeCounterparty.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';

const props = defineProps<{
  event: HistoryEventEntry;
  chain: Blockchain;
  groupLocationLabel?: string;
  icon?: RuiIcons;
  highlight?: boolean;
  hideCustomizedChip?: boolean;
}>();

const { event } = toRefs(props);

const { getEventTypeData } = useHistoryEventMappings();
const attrs = getEventTypeData(event);

const { t } = useI18n({ useScope: 'global' });

const isInformational = computed<boolean>(() => get(event).eventType === 'informational');

const showLocationLabel = computed<boolean>(() => {
  const eventLabel = get(event).locationLabel;
  if (!eventLabel)
    return false;

  const groupLabel = props.groupLocationLabel;
  // Show only when different from group (or no group context)
  return !groupLabel || eventLabel !== groupLabel;
});
</script>

<template>
  <div class="flex items-center text-left">
    <HistoryEventTypeCounterparty
      v-if="('counterparty' in event && event.counterparty) || ('address' in event && event.address)"
      :counterparty="event.counterparty || undefined"
      :address="event.address || undefined"
      :location="event.location"
    >
      <HistoryEventTypeCombination
        :highlight="highlight"
        :icon="icon"
        :type="attrs"
        :show-info="isInformational"
      />
    </HistoryEventTypeCounterparty>
    <HistoryEventTypeCombination
      v-else
      :highlight="highlight"
      :icon="icon"
      :type="attrs"
      :show-info="isInformational"
    />

    <div class="ml-4">
      <div class="font-bold uppercase">
        {{ attrs.label }}
      </div>
      <HistoryEventAccount
        v-if="showLocationLabel"
        :location="event.location"
        :location-label="event.locationLabel!"
        class="text-rui-text-secondary"
      />
      <RuiChip
        v-if="event.customized && !hideCustomizedChip"
        class="mt-1"
        size="sm"
        color="primary"
      >
        <div class="flex items-center gap-2 text-caption font-bold">
          <RuiIcon
            name="lu-square-pen"
            size="14"
          />
          {{ t('transactions.events.customized_event') }}
        </div>
      </RuiChip>
    </div>
  </div>
</template>
