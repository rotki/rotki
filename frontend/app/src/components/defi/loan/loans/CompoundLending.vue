<script setup lang="ts">
import { type PropType } from 'vue';
import { CompoundBorrowingDetails } from '@/premium/premium';
import { type CompoundLoan } from '@/types/defi/compound';

const props = defineProps({
  loan: {
    required: true,
    type: Object as PropType<CompoundLoan>
  }
});

const premium = usePremium();

const { loan } = toRefs(props);

const { assetSymbol } = useAssetInfoRetrieval();
const asset = useRefMap(loan, ({ asset }) => asset);
const symbol = assetSymbol(asset);

const { t } = useI18n();
</script>

<template>
  <VRow>
    <VCol cols="12">
      <LoanHeader v-if="loan.owner" class="mt-8 mb-6" :owner="loan.owner">
        {{ t('compound_lending.header', { asset: symbol }) }}
      </LoanHeader>
      <VRow no-gutters>
        <VCol cols="12" md="6" class="pe-md-4">
          <CompoundCollateral :loan="loan" />
        </VCol>
        <VCol cols="12" md="6" class="pt-8 pt-md-0 ps-md-4">
          <LoanDebt :debt="loan.debt" :asset="loan.asset" />
        </VCol>
      </VRow>
      <VRow no-gutters class="mt-8">
        <VCol cols="12">
          <PremiumCard v-if="!premium" :title="t('compound_lending.history')" />
          <CompoundBorrowingDetails
            v-else
            :owner="loan.owner"
            :assets="[asset]"
          />
        </VCol>
      </VRow>
    </VCol>
  </VRow>
</template>
