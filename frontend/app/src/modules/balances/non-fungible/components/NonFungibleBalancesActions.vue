<script setup lang="ts">
import type { Module } from '@/types/modules';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import NftImageRenderingSettingMenu from '@/components/settings/general/nft/NftImageRenderingSettingMenu.vue';

defineProps<{
  modules: Module[];
  sectionLoading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

function onRefresh(): void {
  emit('refresh');
}
</script>

<template>
  <div class="flex flex-row items-center justify-end gap-2">
    <RuiTooltip>
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="sectionLoading"
          @click="onRefresh()"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </template>
      {{ t('non_fungible_balances.refresh') }}
    </RuiTooltip>
    <ActiveModules :modules="modules" />
    <NftImageRenderingSettingMenu />
  </div>
</template>
