<script setup lang="ts">
import { type LiquityPoolDetailEntry } from '@rotki/common/lib/liquity';
import { type PropType } from 'vue';
import { Section } from '@/types/status';

defineProps({
  pool: {
    required: false,
    type: Object as PropType<LiquityPoolDetailEntry | null>,
    default: null
  }
});

const { t } = useI18n();

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING_POOLS);
</script>

<template>
  <card :loading="loading">
    <template #title>
      {{ t('liquity_pools.title') }}
    </template>
    <template v-if="pool">
      <div class="d-flex align-center py-4 justify-end">
        <balance-display
          :asset="pool.deposited.asset"
          :value="pool.deposited"
          icon-size="32px"
        />
      </div>
      <v-divider />
      <div class="pt-4">
        <div class="d-flex align-center mb-1 justify-space-between">
          <div class="grey--text">{{ t('liquity_pools.rewards') }}</div>
          <div>
            <balance-display
              :asset="pool.rewards.asset"
              :value="pool.rewards"
            />
          </div>
        </div>
        <div class="d-flex align-center mb-1 justify-space-between">
          <div class="grey--text">
            {{ t('liquity_pools.liquidation_gains') }}
          </div>
          <div>
            <balance-display :asset="pool.gains.asset" :value="pool.gains" />
          </div>
        </div>
      </div>
    </template>
    <div v-else class="text-center grey--text pt-4">
      {{ t('liquity_pools.no_lusd_deposited') }}
    </div>
  </card>
</template>
