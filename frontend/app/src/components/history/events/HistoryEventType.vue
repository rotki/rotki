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

const { dark } = useTheme();
const { getEventTypeData } = useHistoryEventMappings();
const attrs = getEventTypeData(event);

const { t } = useI18n();

const onlineEvent = isOnlineHistoryEventRef(event);
const evmOrEthDepositEvent = computed(
  () => get(isEvmEventRef(event)) || get(isEthDepositEventRef(event))
);

const [DefineAvatar, ReuseAvatar] = createReusableTemplate();
const { locationData } = useLocations();
</script>

<template>
  <div class="d-flex align-center text-left">
    <define-avatar #default="{ type }">
      <v-avatar
        class="text--darken-4"
        :color="dark ? 'white' : 'grey lighten-3'"
        :size="36"
      >
        <v-icon :size="20" :color="type.color || 'grey darken-2'">
          {{ type.icon }}
        </v-icon>
      </v-avatar>
    </define-avatar>

    <history-event-type-counterparty
      v-if="evmOrEthDepositEvent"
      :event="evmOrEthDepositEvent"
    >
      <reuse-avatar :type="attrs" />
    </history-event-type-counterparty>
    <reuse-avatar v-else :type="attrs" />

    <div class="ml-4">
      <div class="font-weight-bold text-uppercase">{{ attrs.label }}</div>
      <div v-if="event.locationLabel" class="grey--text d-flex align-center">
        <location-icon
          v-if="onlineEvent"
          icon
          no-padding
          :item="locationData(onlineEvent.location)"
          size="16px"
          class="mr-1"
        />
        <hash-link
          :show-icon="!onlineEvent"
          :no-link="!!onlineEvent"
          :text="event.locationLabel"
          :chain="chain"
          :disable-scramble="!!onlineEvent"
        />
      </div>
      <div v-if="event.customized" class="pt-1">
        <v-chip small label color="primary accent-1">
          <v-icon x-small> mdi-file-document-edit </v-icon>
          <div class="pl-2 text-caption font-weight-bold">
            {{ t('transactions.events.customized_event') }}
          </div>
        </v-chip>
      </div>
    </div>
  </div>
</template>
