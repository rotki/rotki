<script setup lang="ts">
import { useInternalTxConflictResolution } from './use-internal-tx-conflict-resolution';
import { useInternalTxConflictsPanel } from './use-internal-tx-conflicts-panel';

const { t } = useI18n({ useScope: 'global' });
const { cancelResolution, progress } = useInternalTxConflictResolution();
const { showSettings } = useInternalTxConflictsPanel();

const isRunning = computed<boolean>(() => get(progress).isRunning);

function toggleSettings(): void {
  set(showSettings, !get(showSettings));
}
</script>

<template>
  <div class="flex items-center">
    <template v-if="isRunning">
      <span class="text-caption text-rui-text-secondary mr-1 whitespace-nowrap">
        {{ t('internal_tx_conflicts.resolution.progress', { completed: progress.completed, total: progress.total }) }}
      </span>
      <RuiButton
        variant="text"
        icon
        size="sm"
        @click="cancelResolution()"
      >
        <RuiIcon
          size="18"
          name="lu-x"
        />
      </RuiButton>
    </template>
    <RuiTooltip
      v-else
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :active="showSettings"
          data-testid="internal-tx-conflicts-settings"
          @click="toggleSettings()"
        >
          <RuiIcon
            size="18"
            name="lu-settings"
          />
        </RuiButton>
      </template>
      {{ t('internal_tx_conflicts.actions.settings') }}
    </RuiTooltip>
  </div>
</template>
