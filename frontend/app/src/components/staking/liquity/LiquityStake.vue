<script setup lang="ts">
import { type PropType } from 'vue';
import { type LiquityStakingDetail } from '@rotki/common/lib/liquity';

defineProps({
  stake: {
    required: false,
    type: Object as PropType<LiquityStakingDetail | null>,
    default: null
  }
});

const { tc } = useI18n();
</script>

<template>
  <stat-card :title="tc('loan_stake.title')">
    <template v-if="stake">
      <div class="d-flex align-center py-4 justify-end">
        <balance-display
          :asset="stake.staked.asset"
          :value="stake.staked"
          icon-size="32px"
        />
      </div>
      <v-divider />
      <div class="pt-4">
        <div class="d-flex align-center mb-1 justify-space-between">
          <div class="grey--text">{{ tc('loan_stake.rewards') }}</div>
          <div>
            <balance-display
              :asset="stake.lusdRewards.asset"
              :value="stake.lusdRewards"
            />
            <balance-display
              :asset="stake.ethRewards.asset"
              :value="stake.ethRewards"
            />
          </div>
        </div>
      </div>
    </template>
    <div v-else class="text-center grey--text pt-4">
      {{ tc('loan_stake.no_lqty_staked') }}
    </div>
  </stat-card>
</template>
