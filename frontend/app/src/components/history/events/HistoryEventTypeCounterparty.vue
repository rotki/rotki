<script setup lang="ts">
import {
  type EthDepositEvent,
  type EvmHistoryEvent
} from '@/types/history/events';

const props = defineProps<{
  event: EvmHistoryEvent | EthDepositEvent;
}>();

const { event } = toRefs(props);

const { getEventCounterpartyData } = useHistoryEventMappings();

const counterparty = getEventCounterpartyData(event);
const imagePath = '/assets/images/protocols/';
</script>

<template>
  <div>
    <VBadge v-if="counterparty || event.address" avatar overlap color="white">
      <template #badge>
        <VTooltip top>
          <template #activator="{ on }">
            <div v-on="on">
              <VAvatar v-if="counterparty">
                <VIcon v-if="counterparty.icon" :color="counterparty.color">
                  {{ counterparty.icon }}
                </VIcon>

                <VImg
                  v-else-if="counterparty.image"
                  :src="`${imagePath}${counterparty.image}`"
                  contain
                />

                <EnsAvatar v-else :address="counterparty.label" />
              </VAvatar>
              <VAvatar v-else>
                <EnsAvatar :address="event?.address" />
              </VAvatar>
            </div>
          </template>
          <div>{{ counterparty?.label || event?.address }}</div>
        </VTooltip>
      </template>

      <slot />
    </VBadge>
    <slot v-else />
  </div>
</template>
