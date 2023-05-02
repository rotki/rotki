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
    <v-badge v-if="counterparty || event.address" avatar overlap color="white">
      <template #badge>
        <v-tooltip top>
          <template #activator="{ on }">
            <div v-on="on">
              <v-avatar v-if="counterparty">
                <v-icon v-if="counterparty.icon" :color="counterparty.color">
                  {{ counterparty.icon }}
                </v-icon>

                <v-img
                  v-else-if="counterparty.image"
                  :src="`${imagePath}${counterparty.image}`"
                  contain
                />

                <ens-avatar v-else :address="counterparty.label" />
              </v-avatar>
              <v-avatar v-else>
                <ens-avatar :address="event?.address" />
              </v-avatar>
            </div>
          </template>
          <div>{{ counterparty?.label || event?.address }}</div>
        </v-tooltip>
      </template>

      <slot />
    </v-badge>
    <slot v-else />
  </div>
</template>
