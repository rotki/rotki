<template>
  <stat-card :title="$t('loan_stake.title')">
    <loan-row medium :title="$t('loan_stake.stake')">
      <balance-display :asset="stake.asset" :value="stake" :min-width="18" />
    </loan-row>
  </stat-card>
</template>

<script lang="ts">
import { AssetValue } from '@rotki/common/lib/liquity';
import { defineComponent, PropType } from '@vue/composition-api';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

export default defineComponent({
  name: 'LiquityStake',
  components: { LoanRow, StatCard },
  props: {
    stake: {
      required: true,
      type: Object as PropType<AssetValue>
    }
  },
  setup() {
    return {
      assetPadding: 5
    };
  }
});
</script>
