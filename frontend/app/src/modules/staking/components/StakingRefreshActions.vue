<script setup lang="ts">
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

const menuOpen = ref<boolean>(false);

function syncHistory(): void {
  set(menuOpen, false);
  emit('sync-history');
}
</script>

<template>
  <div class="flex items-center gap-2">
    <RuiButtonGroup
      variant="outlined"
      color="primary"
    >
      <RuiTooltip
        :open-delay="400"
        :class-names="{ root: 'flex' }"
      >
        <template #activator>
          <RuiButton
            :data-testid="`${testIdPrefix}-refresh`"
            :loading="refreshing"
            @click="emit('refresh')"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ tooltip }}
      </RuiTooltip>
      <RuiMenu
        v-model="menuOpen"
        :options="{ placement: 'bottom-end' }"
        :class-names="{ root: 'flex' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            v-bind="{
              ...attrs,
              'data-testid': `${testIdPrefix}-refresh-menu`,
            }"
            color="primary"
            variant="outlined"
            class="px-2"
            :aria-label="t('staking_page.refresh_menu.title')"
          >
            <RuiIcon name="lu-chevron-down" />
          </RuiButton>
        </template>

        <div class="w-80 max-w-full py-1">
          <RuiButton
            variant="list"
            :disabled="syncingHistory"
            :data-testid="`${testIdPrefix}-sync-history`"
            @click="syncHistory()"
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
      </RuiMenu>
    </RuiButtonGroup>

    <slot />
  </div>
</template>
