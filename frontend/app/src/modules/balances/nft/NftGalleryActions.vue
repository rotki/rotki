<script setup lang="ts">
import type { Module } from '@/modules/core/common/modules';
import NftImageRenderingSettingMenu from '@/modules/settings/general/nft/NftImageRenderingSettingMenu.vue';
import ActiveModules from '@/modules/settings/modules/ActiveModules.vue';
import RefreshButton from '@/modules/shell/components/RefreshButton.vue';

interface Props {
  modules: Module[];
  loading: boolean;
}

const { loading, modules } = defineProps<Props>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-3">
    <NftImageRenderingSettingMenu />
    <ActiveModules :modules="modules" />
    <RefreshButton
      :loading="loading"
      :tooltip="t('nft_gallery.refresh_tooltip')"
      @refresh="emit('refresh')"
    />
  </div>
</template>
