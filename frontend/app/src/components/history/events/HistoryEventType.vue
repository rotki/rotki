<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type HistoryEventEntry } from '@/types/history/events';
import HistoryEventTypeCounterparty from '@/components/history/events/HistoryEventTypeCounterparty.vue';
import {
  isEthDepositEventRef,
  isEvmEventRef,
  isOnlineHistoryEventRef
} from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  chain: Blockchain;
}>();

const { event } = toRefs(props);

const { getEventTypeData } = useHistoryEventMappings();
const attrs = getEventTypeData(event);

const { t } = useI18n();

const onlineEvent = isOnlineHistoryEventRef(event);
const evmOrEthDepositEvent = computed(
  () => get(isEvmEventRef(event)) || get(isEthDepositEventRef(event))
);
</script>

<template>
  <div class="flex items-center text-left">
    <HistoryEventTypeCounterparty
      v-if="evmOrEthDepositEvent"
      :event="evmOrEthDepositEvent"
    >
      <HistoryEventTypeCombination :type="attrs" />
    </HistoryEventTypeCounterparty>
    <HistoryEventTypeCombination v-else :type="attrs" />

    <div class="ml-4">
      <div class="font-bold text-uppercase">{{ attrs.label }}</div>
      <div v-if="event.locationLabel" class="grey--text flex items-center">
        <LocationIcon
          v-if="onlineEvent"
          icon
          no-padding
          :item="onlineEvent.location"
          size="16px"
          class="mr-1"
        />
        <HashLink
          :show-icon="!onlineEvent"
          :no-link="!!onlineEvent"
          :text="event.locationLabel"
          :chain="chain"
          :disable-scramble="!!onlineEvent"
        />
      </div>
      <div v-if="event.customized" class="pt-1">
        <RuiChip size="sm" color="primary">
          <div class="flex items-center">
            <RuiIcon name="file-edit-line" size="14" />
            <div class="pl-2 text-caption font-bold">
              {{ t('transactions.events.customized_event') }}
            </div>
          </div>
        </RuiChip>
      </div>
    </div>
  </div>
</template>
