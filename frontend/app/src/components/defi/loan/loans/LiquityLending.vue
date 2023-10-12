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
  <div class="flex flex-col gap-4">
    <LoanHeader :owner="loan.owner">
      {{
        t('liquity_lending.header', {
          troveId: scrambleIdentifier(loan.balance.troveId)
        })
      }}
    </LoanHeader>

    <div class="grid md:grid-cols-2 gap-4">
      <LiquityCollateral :collateral="collateral" :ratio="ratio" />
      <LiquityLiquidation
        v-if="liquidationPrice"
        :price="liquidationPrice"
        :asset="collateral.asset"
      />
      <LoanDebt :debt="debt" :asset="debt.asset" />
    </div>

    <PremiumCard v-if="!premium" :title="t('liquity_lending.trove_events')" />
    <HistoryEventsView
      use-external-account-filter
      :section-title="t('liquity_lending.trove_events')"
      :protocols="['liquity']"
      :external-account-filter="[{ chain, address: loan.owner }]"
      :only-chains="[chain]"
      :entry-types="[HistoryEventEntryType.EVM_EVENT]"
    />
  </div>
</template>
