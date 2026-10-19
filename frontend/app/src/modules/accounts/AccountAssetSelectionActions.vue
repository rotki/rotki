<script setup lang="ts">
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';

const {
  disabled = false,
  selectedCount = 0,
  selectionMode,
  showSelectionToggle,
} = defineProps<{
  disabled?: boolean;
  selectedCount?: number;
  selectionMode: boolean;
  showSelectionToggle: boolean;
}>();

const emit = defineEmits<{
  'clear-selection': [];
  'ignore': [ignored: boolean];
  'mark-spam': [];
  'toggle-mode': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <template v-if="showSelectionToggle">
    <TableSelectionBar
      v-if="selectionMode"
      class="grow"
      :count="selectedCount"
      exitable
      @clear="emit('clear-selection')"
      @exit="emit('toggle-mode')"
    >
      <TableSelectionAction
        icon="lu-eye-off"
        :disabled="selectedCount === 0"
        :title="t('ignore_buttons.ignore_tooltip')"
        data-testid="account-assets-ignore"
        @click="emit('ignore', true)"
      >
        {{ t('ignore_buttons.ignore') }}
      </TableSelectionAction>
      <TableSelectionAction
        icon="lu-trash-2"
        color="error"
        :disabled="selectedCount === 0"
        :title="t('asset_table.mark_spam_tooltip')"
        data-testid="account-assets-mark-spam"
        @click="emit('mark-spam')"
      >
        {{ t('asset_table.mark_spam') }}
      </TableSelectionAction>
    </TableSelectionBar>
    <RuiTooltip
      v-else
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          :disabled="disabled"
          data-testid="account-assets-select"
          @click="emit('toggle-mode')"
        >
          <template #prepend>
            <RuiIcon
              name="lu-copy-check"
              size="18"
            />
          </template>
          {{ t('common.actions.select') }}
        </RuiButton>
      </template>
      {{ t('account_balances.enter_selection_mode') }}
    </RuiTooltip>
  </template>
</template>
