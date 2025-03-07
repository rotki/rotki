<script setup lang="ts">
import type { LiquityPoolDetailEntry } from '@rotki/common';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';

defineProps<{ pool: LiquityPoolDetailEntry | null }>();

const { t } = useI18n();

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING_POOLS);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('liquity_pools.title') }}
    </template>
    <template v-if="pool">
      <div class="flex items-center justify-end">
        <BalanceDisplay
          :asset="pool.deposited.asset"
          :value="pool.deposited"
          icon-size="32px"
          :loading="loading"
        />
      </div>
      <RuiDivider class="my-4" />
      <div class="flex flex-col gap-1">
        <div class="flex items-center justify-between">
          <div class="text-rui-text-secondary">
            {{ t('liquity_pools.rewards') }}
          </div>
          <div>
            <BalanceDisplay
              :asset="pool.rewards.asset"
              :value="pool.rewards"
              :loading="loading"
            />
          </div>
        </div>
        <div class="flex items-center justify-between">
          <div class="text-rui-text-secondary">
            {{ t('liquity_pools.liquidation_gains') }}
          </div>
          <div>
            <BalanceDisplay
              :asset="pool.gains.asset"
              :value="pool.gains"
              :loading="loading"
            />
          </div>
        </div>
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
