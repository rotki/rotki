<script setup lang="ts">
import { type InternalTxConflict, InternalTxConflictActions } from './types';

const { row, resolving, disabled, actionLabel, highlighted } = defineProps<{
  row: InternalTxConflict;
  resolving: boolean;
  disabled: boolean;
  actionLabel: string;
  highlighted: boolean;
}>();

const emit = defineEmits<{
  'resolve': [];
  'show-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :color="row.action === InternalTxConflictActions.REPULL ? 'primary' : 'warning'"
          :loading="resolving"
          :disabled="disabled || resolving"
          @click="emit('resolve')"
        >
          <RuiIcon
            :name="row.action === InternalTxConflictActions.REPULL ? 'lu-refresh-cw' : 'lu-wrench'"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('internal_tx_conflicts.resolution.resolve') }} ({{ actionLabel }})
    </RuiTooltip>
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="!row.groupIdentifier"
          :color="highlighted ? 'warning' : undefined"
          @click="emit('show-in-events')"
        >
          <RuiIcon
            :name="highlighted ? 'lu-eye-off' : 'lu-external-link'"
            size="16"
          />
        </RuiButton>
      </template>
      {{ highlighted
        ? t('internal_tx_conflicts.actions.clear_highlight')
        : t('internal_tx_conflicts.actions.show_in_events')
      }}
    </RuiTooltip>
  </div>
</template>
