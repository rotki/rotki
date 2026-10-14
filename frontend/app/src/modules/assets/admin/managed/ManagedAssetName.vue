<script setup lang="ts">
import type { AssetDisplay } from '@/modules/assets/admin/use-asset-display-helpers';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';

defineProps<{
  asset: AssetDisplay;
  rebasing: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-2 min-w-0">
    <AssetDetailsBase
      class="min-w-0"
      :asset="asset"
    />
    <RuiChip
      v-if="rebasing"
      color="primary"
      size="sm"
      variant="outlined"
      class="shrink-0"
    >
      {{ t('common.rebasing_token') }}
    </RuiChip>
  </div>
</template>
