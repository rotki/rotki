<script setup lang="ts">
import { AaveBorrowingDetails } from '@/premium/premium';
import { type AaveLoan } from '@/types/defi/lending';
import { Section } from '@/types/status';

const props = defineProps<{ loan: AaveLoan }>();

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
  <div class="flex flex-col gap-4">
    <LoanHeader v-if="loan.owner" :owner="loan.owner">
      {{ t('aave_lending.header', { asset: symbol }) }}
    </LoanHeader>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <AaveCollateral :loan="loan" />
      <LoanDebt :debt="loan.debt" :asset="loan.asset" />
    </div>

    <PremiumCard v-if="!premium" :title="t('aave_lending.history')" />

    <AaveBorrowingDetails
      v-else
      :loading="aaveHistoryLoading"
      :owner="loan.owner"
      :total-lost="loan.totalLost"
      :liquidation-earned="loan.liquidationEarned"
    />
  </div>
</template>
