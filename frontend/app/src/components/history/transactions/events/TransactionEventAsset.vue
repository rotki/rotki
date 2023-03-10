<script setup lang="ts">
import { type Ref } from 'vue';
import {
  TransactionEventProtocol,
  TransactionEventType
} from '@rotki/common/lib/history/tx-events';
import { getEventType } from '@/utils/history';
import { type EthTransactionEventEntry } from '@/types/history/tx';

const props = withDefaults(
  defineProps<{
    event: EthTransactionEventEntry;
    showEventDetail?: boolean;
  }>(),
  {
    showEventDetail: false
  }
);

const { tc } = useI18n();

const { event } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const showBalance = computed<boolean>(() => {
  const type = getEventType(get(event));
  return (
    !type ||
    ![
      TransactionEventType.APPROVAL,
      TransactionEventType.INFORMATIONAL
    ].includes(type)
  );
});

const eventAsset = computed(() => get(event).asset);
const symbol = assetSymbol(eventAsset);

const extraDataPanel: Ref<number[]> = ref([]);
</script>
<template>
  <div>
    <div class="py-2 d-flex align-center">
      <div class="mr-2">
        <asset-link :asset="event.asset" icon>
          <asset-icon size="32px" :identifier="event.asset" />
        </asset-link>
      </div>
      <div v-if="showBalance">
        <div>
          <amount-display :value="event.balance.amount" :asset="event.asset" />
        </div>
        <div>
          <amount-display
            :value="event.balance.usdValue"
            fiat-currency="USD"
            class="grey--text"
            :timestamp="event.timestamp"
          />
        </div>
      </div>
      <div v-else>
        {{ symbol }}
      </div>
    </div>
    <v-expansion-panels
      v-if="
        showEventDetail &&
        event.hasDetails &&
        event.counterparty === TransactionEventProtocol.LIQUITY
      "
      v-model="extraDataPanel"
      multiple
    >
      <v-expansion-panel>
        <v-expansion-panel-header>
          <template #default="{ open }">
            <div class="success--text font-weight-bold">
              {{
                open
                  ? tc('liquity_staking_details.view.hide')
                  : tc('liquity_staking_details.view.show')
              }}
            </div>
          </template>
        </v-expansion-panel-header>
        <v-expansion-panel-content class="pt-4">
          <transaction-event-liquity-extra-data :event="event" />
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>
