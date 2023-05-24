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
  <v-row>
    <v-col cols="12">
      <loan-header v-if="loan.owner" class="mt-8 mb-6" :owner="loan.owner">
        {{ t('aave_lending.header', { asset: symbol }) }}
      </loan-header>
      <v-row>
        <v-col cols="12" md="6">
          <aave-collateral :loan="loan" />
        </v-col>

        <v-col cols="12" md="6">
          <loan-debt :debt="loan.debt" :asset="loan.asset" />
        </v-col>
      </v-row>
      <v-row no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card v-if="!premium" :title="t('aave_lending.history')" />
          <aave-borrowing-details
            v-else
            :loading="aaveHistoryLoading"
            :owner="loan.owner"
            :total-lost="loan.totalLost"
            :liquidation-earned="loan.liquidationEarned"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
