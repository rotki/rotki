<script setup lang="ts">
import type { AssetBalance } from '@rotki/common';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';

const selection = defineModel<'current' | 'historical'>({ required: true });

defineProps<{
  loading: boolean;
  received: AssetBalance[];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard
    no-padding
    class="mb-4"
  >
    <template #custom-header>
      <div class="flex items-center justify-between p-4">
        <h6 class="text-h6">
          {{ t('kraken_staking_received.title') }}
        </h6>
        <RuiButtonGroup
          v-model="selection"
          required
          variant="outlined"
          color="primary"
        >
          <RuiButton model-value="current">
            {{ t('kraken_staking_received.switch.current') }}
          </RuiButton>
          <RuiButton model-value="historical">
            {{ t('kraken_staking_received.switch.historical') }}
          </RuiButton>
        </RuiButtonGroup>
      </div>
    </template>
    <div class="p-4 py-0 max-h-[11rem]">
      <div
        v-for="item in received"
        :key="item.asset"
        class="flex items-center justify-between"
      >
        <AssetDetails
          :asset="item.asset"
          dense
        />
        <div class="flex items-center gap-3">
          <ValueAccuracyHint v-if="selection === 'historical'" />
          <BalanceDisplay
            no-icon
            :asset="item.asset"
            :value="item"
            :loading="loading && selection === 'current'"
          />
        </div>
      </div>
    </div>
  </RuiCard>
</template>
