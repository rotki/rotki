<script setup lang="ts">
import { type AssetBalance, type BigNumber } from '@rotki/common';
import { type ComputedRef, type PropType } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
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
const { t } = useI18n();
const { scrambleIdentifier } = useScramble();
const chain = Blockchain.ETH;
</script>

<template>
  <VRow>
    <VCol cols="12">
      <LoanHeader class="mt-8 mb-6" :owner="loan.owner">
        {{
          t('liquity_lending.header', {
            troveId: scrambleIdentifier(loan.balance.troveId)
          })
        }}
      </LoanHeader>
      <VRow no-gutters>
        <VCol cols="12" md="6" class="pe-md-4">
          <LiquityCollateral :collateral="collateral" :ratio="ratio" />
        </VCol>
        <VCol
          v-if="liquidationPrice"
          cols="12"
          md="6"
          class="ps-md-4 pt-8 pt-md-0"
        >
          <LiquityLiquidation
            :price="liquidationPrice"
            :asset="collateral.asset"
          />
        </VCol>
        <VCol
          cols="12"
          md="6"
          class=""
          :class="{
            'pt-8 ps-md-0 pe-md-4': !!liquidationPrice,
            'ps-md-4': !liquidationPrice
          }"
        >
          <LoanDebt :debt="debt" :asset="debt.asset" />
        </VCol>
      </VRow>
      <div v-if="!premium" class="mt-8">
        <PremiumCard :title="t('liquity_lending.trove_events')" />
      </div>
      <div v-else>
        <HistoryEventsView
          use-external-account-filter
          :section-title="t('liquity_lending.trove_events')"
          :protocols="['liquity']"
          :external-account-filter="[{ chain, address: loan.owner }]"
          :only-chains="[chain]"
          :entry-types="[HistoryEventEntryType.EVM_EVENT]"
        />
      </div>
    </VCol>
  </VRow>
</template>
