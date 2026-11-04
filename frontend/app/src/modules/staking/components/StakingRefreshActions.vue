<script setup lang="ts">
import RefreshSplitButton from '@/modules/shell/components/RefreshSplitButton.vue';

/**
 * A staking page's actions, as on the balances pages: one Refresh for the page's figures and its
 * events, with the full history sync in its menu, then the page's settings in the default slot.
 */
const { testIdPrefix } = defineProps<{
  refreshing: boolean;
  syncingHistory: boolean;
  /** What Refresh covers on this page. */
  tooltip: string;
  /** Prefixes the test ids: `<prefix>-refresh`, `<prefix>-refresh-menu`, `<prefix>-sync-history`. */
  testIdPrefix: string;
  /** The chain whose transactions the history sync queries, named in its description. */
  chainName: string;
}>();

const emit = defineEmits<{
  'refresh': [];
  'sync-history': [];
}>();

defineSlots<{
  default?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-2">
    <RefreshSplitButton
      :test-id="`${testIdPrefix}-refresh`"
      :menu-label="t('staking_page.refresh_menu.title')"
      :tooltip="tooltip"
      :loading="refreshing"
      @refresh="emit('refresh')"
    >
      <template #default="{ close }">
        <div class="w-80 max-w-full py-1">
          <RuiButton
            variant="list"
            :disabled="syncingHistory"
            :data-testid="`${testIdPrefix}-sync-history`"
            @click="close(); emit('sync-history')"
          >
            <template #prepend>
              <RuiIcon
                size="18"
                name="lu-history"
              />
            </template>
            <span class="flex flex-col items-start text-left">
              <span>{{ t('staking_page.refresh_menu.sync_history') }}</span>
              <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
                {{ t('staking_page.refresh_menu.sync_history_description', { chain: chainName }) }}
              </span>
            </span>
          </RuiButton>
        </div>
      </template>
    </RefreshSplitButton>

    <slot />
  </div>
</template>
