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
  <v-row>
    <v-col cols="12">
      <loan-header v-if="loan.owner" class="mt-8 mb-6" :owner="loan.owner">
        {{ t('compound_lending.header', { asset: symbol }) }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <compound-collateral :loan="loan" />
        </v-col>
        <v-col cols="12" md="6" class="pt-8 pt-md-0 ps-md-4">
          <loan-debt :debt="loan.debt" :asset="loan.asset" />
        </v-col>
      </v-row>
      <v-row no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="t('compound_lending.history')"
          />
          <compound-borrowing-details
            v-else
            :owner="loan.owner"
            :assets="[asset]"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
