<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { assetSymbolToIdentifierMap } from '@rotki/common/lib/data';
import Fragment from '@/components/helper/Fragment';

const props = defineProps<{
  totalInterestOwed: BigNumber;
  stabilityFee: string;
  loading: boolean;
}>();

const premium = usePremium();
const { totalInterestOwed } = toRefs(props);
const { t } = useI18n();
const interest = computed(() => {
  if (get(totalInterestOwed).isNegative()) {
    return Zero;
  }
  return get(totalInterestOwed);
});

const dai: string = assetSymbolToIdentifierMap.DAI;
const assetPadding = 4;
</script>

<template>
  <Fragment>
    <RuiDivider class="my-4" />
    <LoanRow :title="t('makerdao_vault_debt.stability_fee')" class="mb-2">
      <PercentageDisplay :value="stabilityFee" :asset-padding="assetPadding" />
    </LoanRow>
    <LoanRow :title="t('makerdao_vault_debt.total_lost')">
      <div v-if="premium">
        <AmountDisplay
          :asset-padding="assetPadding"
          :value="interest"
          :loading="loading"
          :asset="dai"
        />
      </div>
      <div v-else>
        <PremiumLock />
      </div>
    </LoanRow>
  </Fragment>
</template>
