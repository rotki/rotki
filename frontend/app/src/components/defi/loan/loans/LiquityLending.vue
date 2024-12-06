<script setup lang="ts">
import { type AssetBalance, type BigNumber, Blockchain, HistoryEventEntryType } from '@rotki/common';
import { useScramble } from '@/composables/scramble';
import { usePremium } from '@/composables/premium';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LiquityLiquidation from '@/components/defi/loan/loans/liquity/LiquityLiquidation.vue';
import LiquityCollateral from '@/components/defi/loan/loans/liquity/LiquityCollateral.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import type { LiquityLoan } from '@/types/defi/liquity';

const props = defineProps<{
  loan: LiquityLoan;
}>();

const { t } = useI18n();
const { loan } = toRefs(props);

const debt = computed<AssetBalance>(() => get(loan).balance.debt);
const collateral = computed<AssetBalance>(() => get(loan).balance.collateral);
const ratio = computed<BigNumber | null>(() => get(loan).balance.collateralizationRatio);
const liquidationPrice = computed<BigNumber | null>(() => get(loan).balance.liquidationPrice);
const premium = usePremium();

const { scrambleIdentifier } = useScramble();
const chain = Blockchain.ETH;
</script>

<template>
  <div class="flex flex-col gap-4">
    <LoanHeader :owner="loan.owner">
      {{
        t('liquity_lending.header', {
          troveId: scrambleIdentifier(loan.balance.troveId),
        })
      }}
    </LoanHeader>

    <div class="grid md:grid-cols-2 gap-4">
      <LiquityCollateral
        :collateral="collateral"
        :ratio="ratio"
      />
      <LiquityLiquidation
        v-if="liquidationPrice"
        :price="liquidationPrice"
        :asset="collateral.asset"
      />
      <LoanDebt
        :debt="debt"
        :asset="debt.asset"
      />
    </div>

    <PremiumCard
      v-if="!premium"
      :title="t('liquity_lending.trove_events')"
    />
    <HistoryEventsView
      v-else
      use-external-account-filter
      :section-title="t('liquity_lending.trove_events')"
      :protocols="['liquity']"
      :external-account-filter="[{ chain, address: loan.owner }]"
      :only-chains="[chain]"
      :entry-types="[HistoryEventEntryType.EVM_EVENT]"
    />
  </div>
</template>
