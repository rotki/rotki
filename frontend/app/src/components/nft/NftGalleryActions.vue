<script setup lang="ts">
import type { Module } from '@/types/modules';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import NftImageRenderingSettingMenu from '@/components/settings/general/nft/NftImageRenderingSettingMenu.vue';

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
