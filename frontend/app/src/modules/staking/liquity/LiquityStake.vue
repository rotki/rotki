<script setup lang="ts">
import type { LiquityStakingDetailEntry } from '@rotki/common';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import StakingHeadlineBalance from '@/modules/staking/components/StakingHeadlineBalance.vue';
import { liquityActivity } from '@/modules/staking/liquity/liquity.activity';
import { ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { stake = null } = defineProps<{
  stake?: LiquityStakingDetailEntry | null;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const loading = useIsActive(liquityActivity.kind, ...liquityActivity.partsOf({ part: ActivityPart.STAKE }));
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('loan_stake.title') }}
    </template>
    <template v-if="stake">
      <StakingHeadlineBalance
        :asset="stake.staked.asset"
        :value="stake.staked"
        :loading="loading"
      />
      <RuiDivider class="my-4" />
      <div class="grid grid-cols-[1fr_auto] items-center gap-x-4">
        <div class="text-rui-text-secondary">
          {{ t('loan_stake.unclaimed_rewards') }}
        </div>
        <BalanceDisplay
          :asset="stake.lusdRewards.asset"
          :value="stake.lusdRewards"
          :loading="loading"
        />
        <div />
        <BalanceDisplay
          :asset="stake.ethRewards.asset"
          :value="stake.ethRewards"
          :loading="loading"
        />
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
