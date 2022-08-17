<template>
  <stat-card :title="tc('loan_stake.title')">
    <loan-row medium :title="tc('loan_stake.stake')">
      <balance-display :asset="stake.asset" :value="stake" />
    </loan-row>
  </stat-card>
</template>

<script lang="ts">
import { AssetBalance } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

export default defineComponent({
  name: 'LiquityStake',
  components: { LoanRow, StatCard },
  props: {
    stake: {
      required: true,
      type: Object as PropType<AssetBalance>
    }
  },
  setup() {
    const { tc } = useI18n();
    return {
      assetPadding: 5,
      tc
    };
  }
});
</script>
