<script setup lang="ts">
import type { Blockchain } from '@rotki/common';
import type { RuiIcons } from '@rotki/ui-library';
import type { AssetMovementEvent, HistoryEventEntry, OnlineHistoryEvent } from '@/types/history/events/schemas';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import HistoryEventTypeCounterparty from '@/components/history/events/HistoryEventTypeCounterparty.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useSupportedChains } from '@/composables/info/chains';
import HashLink from '@/modules/common/links/HashLink.vue';
import {
  isAssetMovementEvent,
  isOnlineHistoryEvent,
} from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  chain: Blockchain;
  icon?: RuiIcons;
  highlight?: boolean;
}>();

const { event } = toRefs(props);

const { getEventTypeData } = useHistoryEventMappings();
const attrs = getEventTypeData(event);
const { getChain } = useSupportedChains();

const { t } = useI18n({ useScope: 'global' });

const exchangeEvent = computed<AssetMovementEvent | OnlineHistoryEvent | undefined>(() => {
  const event = props.event;
  if ((isOnlineHistoryEvent(event) && !getChain(event.location, undefined)) || isAssetMovementEvent(event)) {
    return event;
  }

  return undefined;
});

const isInformational = computed(() => get(event).eventType === 'informational');
</script>

<template>
  <div class="flex items-center text-left">
    <HistoryEventTypeCounterparty
      v-if="('counterparty' in event && event.counterparty) || 'address' in event"
      :event="event"
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
      <div
        v-if="event.locationLabel"
        class="text-rui-text-secondary flex items-center"
      >
        <LocationIcon
          v-if="exchangeEvent"
          icon
          :item="exchangeEvent.location"
          size="16px"
          class="mr-2"
        />
        <HashLink
          :text="event.locationLabel"
          :location="event.location"
        />
      </div>
      <RuiChip
        v-if="event.customized"
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
