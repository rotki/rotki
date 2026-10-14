<script setup lang="ts">
import type { LiquityPoolDetailEntry } from '@rotki/common';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import StakingHeadlineBalance from '@/modules/staking/components/StakingHeadlineBalance.vue';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

defineProps<{ pool: LiquityPoolDetailEntry | null }>();

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const loading = useIsActive(ActivityKind.LIQUITY, ActivityPart.POOLS);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('liquity_pools.title') }}
    </template>
    <template v-if="pool">
      <StakingHeadlineBalance
        :asset="pool.deposited.asset"
        :value="pool.deposited"
        :loading="loading"
      />
      <RuiDivider class="my-4" />
      <div class="grid grid-cols-[1fr_auto] items-center gap-x-4">
        <div class="text-rui-text-secondary">
          {{ t('liquity_pools.rewards') }}
        </div>
        <BalanceDisplay
          :asset="pool.rewards.asset"
          :value="pool.rewards"
          :loading="loading"
        />
        <div class="text-rui-text-secondary">
          {{ t('liquity_pools.liquidation_gains') }}
        </div>
        <BalanceDisplay
          :asset="pool.gains.asset"
          :value="pool.gains"
          :loading="loading"
        />
      </div>
    </template>
    <div
      v-else
      class="text-center text-rui-text-secondary pb-4"
    >
      {{ t('liquity_pools.no_lusd_deposited') }}
    </div>
  </RuiCard>
</template>
