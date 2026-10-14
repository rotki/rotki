<script setup lang="ts">
import NftSettingsMenu from '@/modules/balances/nft/NftSettingsMenu.vue';

const { loading } = defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-2">
    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="loading"
          data-testid="nft-gallery-refresh"
          @click="emit('refresh')"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </template>
      {{ t('nft_gallery.refresh_tooltip') }}
    </RuiTooltip>
    <NftSettingsMenu />
  </div>
</template>
