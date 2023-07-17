<script setup lang="ts">
import { type PropType } from 'vue';
import { AaveBorrowingDetails } from '@/premium/premium';
import { type AaveLoan } from '@/types/defi/lending';
import { Section } from '@/types/status';

const props = defineProps({
  loan: {
    required: true,
    type: Object as PropType<AaveLoan>
  }
});

const { loan } = toRefs(props);
const premium = usePremium();

const { isLoading } = useStatusStore();
const aaveHistoryLoading = isLoading(Section.DEFI_AAVE_HISTORY);

const { assetSymbol } = useAssetInfoRetrieval();
const asset = useRefMap(loan, ({ asset }) => asset);
const symbol = assetSymbol(asset);

const { t } = useI18n();
</script>

<template>
  <VRow>
    <VCol cols="12">
      <LoanHeader v-if="loan.owner" class="mt-8 mb-6" :owner="loan.owner">
        {{ t('aave_lending.header', { asset: symbol }) }}
      </LoanHeader>
      <VRow>
        <VCol cols="12" md="6">
          <AaveCollateral :loan="loan" />
        </VCol>

        <VCol cols="12" md="6">
          <LoanDebt :debt="loan.debt" :asset="loan.asset" />
        </VCol>
      </VRow>
      <VRow no-gutters class="mt-8">
        <VCol cols="12">
          <PremiumCard v-if="!premium" :title="t('aave_lending.history')" />
          <AaveBorrowingDetails
            v-else
            :loading="aaveHistoryLoading"
            :owner="loan.owner"
            :total-lost="loan.totalLost"
            :liquidation-earned="loan.liquidationEarned"
          />
        </VCol>
      </VRow>
    </VCol>
  </VRow>
</template>
