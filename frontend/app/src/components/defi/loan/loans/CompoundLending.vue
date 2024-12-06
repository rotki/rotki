<script setup lang="ts">
import { CompoundBorrowingDetails } from '@/premium/premium';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { usePremium } from '@/composables/premium';
import PremiumCard from '@/components/display/PremiumCard.vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import CompoundCollateral from '@/components/defi/loan/loans/compound/CompoundCollateral.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import type { CompoundLoan } from '@/types/defi/compound';

const props = defineProps<{ loan: CompoundLoan }>();

const premium = usePremium();

const { loan } = toRefs(props);

const { assetSymbol } = useAssetInfoRetrieval();
const asset = useRefMap(loan, ({ asset }) => asset);
const symbol = assetSymbol(asset);

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-col gap-4">
    <LoanHeader
      v-if="loan.owner"
      :owner="loan.owner"
    >
      {{ t('compound_lending.header', { asset: symbol }) }}
    </LoanHeader>

    <div class="grid md:grid-cols-2 gap-4">
      <CompoundCollateral :loan="loan" />
      <LoanDebt
        :debt="loan.debt"
        :asset="loan.asset"
      />
    </div>

    <PremiumCard
      v-if="!premium"
      :title="t('compound_lending.history')"
    />
    <CompoundBorrowingDetails
      v-else
      :owner="loan.owner"
      :assets="[asset]"
    />
  </div>
</template>
