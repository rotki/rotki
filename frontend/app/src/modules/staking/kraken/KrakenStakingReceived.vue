<script setup lang="ts">
import type { AssetBalance } from '@rotki/common';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import ValueAccuracyHint from '@/modules/shell/components/ValueAccuracyHint.vue';

const selection = defineModel<'current' | 'historical'>({ required: true });

defineProps<{
  loading: boolean;
  received: AssetBalance[];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard no-padding>
    <template #custom-header>
      <div class="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
        <h6 class="text-base font-semibold text-rui-text">
          {{ t('kraken_staking_received.title') }}
        </h6>
        <div class="flex items-center gap-1">
          <ValueAccuracyHint v-if="selection === 'historical'" />
          <RuiButtonGroup
            v-model="selection"
            variant="segmented"
            required
          >
            <RuiButton model-value="current">
              {{ t('kraken_staking_received.switch.current') }}
            </RuiButton>
            <RuiButton model-value="historical">
              {{ t('kraken_staking_received.switch.historical') }}
            </RuiButton>
          </RuiButtonGroup>
        </div>
      </div>
    </template>
    <div class="px-4 pb-2">
      <div
        v-for="item in received"
        :key="item.asset"
        class="flex items-center justify-between"
      >
        <AssetDetails
          :asset="item.asset"
          :display="{ dense: true }"
        />
        <BalanceDisplay
          no-icon
          :asset="item.asset"
          :value="item"
          :loading="loading && selection === 'current'"
        />
      </div>
    </div>
  </RuiCard>
</template>
