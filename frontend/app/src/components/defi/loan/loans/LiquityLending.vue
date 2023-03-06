<script setup lang="ts">
import { type AssetBalance, type BigNumber } from '@rotki/common';
import { type ComputedRef, type PropType } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol
} from '@rotki/common/lib/history/tx-events';
import { type LiquityLoan } from '@/types/defi/liquity';

const props = defineProps({
  loan: {
    required: true,
    type: Object as PropType<LiquityLoan>
  }
});

const { loan } = toRefs(props);
const debt: ComputedRef<AssetBalance> = computed(() => get(loan).balance.debt);
const collateral: ComputedRef<AssetBalance> = computed(
  () => get(loan).balance.collateral
);
const ratio: ComputedRef<BigNumber | null> = computed(
  () => get(loan).balance.collateralizationRatio
);
const liquidationPrice: ComputedRef<BigNumber | null> = computed(
  () => get(loan).balance.liquidationPrice
);
const premium = usePremium();
const { tc } = useI18n();
const chain = Blockchain.ETH;
</script>

<template>
  <v-row>
    <v-col cols="12">
      <loan-header class="mt-8 mb-6" :owner="loan.owner">
        {{ tc('liquity_lending.header', 0, { troveId: loan.balance.troveId }) }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <liquity-collateral :collateral="collateral" :ratio="ratio" />
        </v-col>
        <v-col
          v-if="liquidationPrice"
          cols="12"
          md="6"
          class="ps-md-4 pt-8 pt-md-0"
        >
          <liquity-liquidation
            :price="liquidationPrice"
            :asset="collateral.asset"
          />
        </v-col>
        <v-col
          cols="12"
          md="6"
          class=""
          :class="{
            'pt-8 ps-md-0 pe-md-4': !!liquidationPrice,
            'ps-md-4': !liquidationPrice
          }"
        >
          <loan-debt :debt="debt" :asset="debt.asset" />
        </v-col>
      </v-row>
      <div v-if="!premium" class="mt-8">
        <premium-card :title="tc('liquity_lending.trove_events')" />
      </div>
      <div v-else>
        <transaction-content
          use-external-account-filter
          :section-title="tc('liquity_lending.trove_events')"
          :protocols="[TransactionEventProtocol.LIQUITY]"
          :event-types="[
            HistoryEventType.WITHDRAWAL,
            HistoryEventType.SPEND,
            HistoryEventType.DEPOSIT
          ]"
          :event-sub-types="[
            HistoryEventSubType.DEPOSIT_ASSET,
            HistoryEventSubType.REMOVE_ASSET,
            HistoryEventSubType.GENERATE_DEBT,
            HistoryEventSubType.PAYBACK_DEBT
          ]"
          :external-account-filter="[{ chain, address: loan.owner }]"
          :only-chains="[chain]"
        />
      </div>
    </v-col>
  </v-row>
</template>
