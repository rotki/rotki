<script lang="ts" setup>
import type { AssetMovementEntry } from '@/types/history/asset-movements';

defineProps<{ item: AssetMovementEntry }>();

const { t } = useI18n();
</script>

<template>
  <div>
    <h6 class="text-h6 mb-4">
      {{ t('deposits_withdrawals.details.title') }}
    </h6>
    <RuiCard>
      <MovementLinks
        v-if="item.address || item.transactionId"
        :item="item"
      />
      <div
        v-else
        class="font-medium"
      >
        {{ t('deposits_withdrawals.details.no_details') }}
      </div>
    </RuiCard>
  </div>
</template>
