<script setup lang="ts">
import type { LiquityStakingDetailEntry } from '@rotki/common';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';

withDefaults(
  defineProps<{
    stake?: LiquityStakingDetailEntry | null;
  }>(),
  {
    stake: null,
  },
);

const { t } = useI18n();

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('loan_stake.title') }}
    </template>
    <template v-if="stake">
      <div class="flex items-center justify-end">
        <BalanceDisplay
          :asset="stake.staked.asset"
          :value="stake.staked"
          icon-size="32px"
          :loading="loading"
        />
      </div>
      <RuiDivider class="my-4" />
      <div class="flex items-center justify-between">
        <div class="text-rui-text-secondary">
          {{ t('loan_stake.unclaimed_rewards') }}
        </div>
        <div class="flex flex-col gap-1">
          <BalanceDisplay
            :asset="stake.lusdRewards.asset"
            :value="stake.lusdRewards"
            :loading="loading"
          />
          <BalanceDisplay
            :asset="stake.ethRewards.asset"
            :value="stake.ethRewards"
            :loading="loading"
          />
        </div>
      </div>
    </template>
    <div
      v-else
      class="text-center text-rui-text-secondary pb-4"
    >
      {{ t('loan_stake.no_lqty_staked') }}
    </div>
  </RuiCard>
</template>
