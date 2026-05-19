<script setup lang="ts">
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { isChainTab, type RpcSettingTab } from '@/modules/settings/general/rpc/use-rpc-settings-tabs';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { tab, groupLabel } = defineProps<{
  tab: RpcSettingTab;
  groupLabel?: string;
}>();
</script>

<template>
  <div class="flex flex-col w-full">
    <div
      v-if="groupLabel"
      class="px-3 pt-2 pb-1 -mx-3 mb-1 text-xs font-medium uppercase tracking-wider text-rui-text-secondary border-t border-default"
    >
      {{ groupLabel }}
    </div>
    <div class="flex items-center gap-2">
      <LocationDisplay
        v-if="isChainTab(tab)"
        :open-details="false"
        :identifier="tab.chain"
        horizontal
        size="20px"
      />
      <AppImage
        v-else
        :src="tab.image"
        size="20px"
        contain
        class="icon-bg"
      />
      <span
        v-if="!isChainTab(tab)"
        class="text-rui-text-secondary"
      >
        {{ tab.name }}
      </span>
    </div>
  </div>
</template>
