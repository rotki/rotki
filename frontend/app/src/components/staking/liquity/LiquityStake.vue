<script setup lang="ts">
import { type LiquityStakingDetailEntry } from '@rotki/common/lib/liquity';
import { Section } from '@/types/status';

withDefaults(
  defineProps<{
    stake?: LiquityStakingDetailEntry | null;
  }>(),
  {
    stake: null
  }
);

const { t } = useI18n();

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING);
</script>

<template>
  <card :loading="loading">
    <template #title> {{ t('loan_stake.title') }} </template>
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
          <div class="grey--text">{{ t('loan_stake.unclaimed_rewards') }}</div>
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
      {{ t('loan_stake.no_lqty_staked') }}
    </div>
  </card>
</template>
