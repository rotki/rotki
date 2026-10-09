<script setup lang="ts">
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
      <RuiButton
        size="sm"
        variant="outlined"
        :disabled="selectedCount === 0"
        :title="t('ignore_buttons.ignore_tooltip')"
        data-testid="account-assets-ignore"
        @click="emit('ignore', true)"
      >
        <template #prepend>
          <RuiIcon
            name="lu-eye-off"
            size="16"
          />
        </template>
        {{ t('ignore_buttons.ignore') }}
      </RuiButton>
      <RuiButton
        size="sm"
        variant="outlined"
        color="error"
        :disabled="selectedCount === 0"
        :title="t('asset_table.mark_spam_tooltip')"
        data-testid="account-assets-mark-spam"
        @click="emit('mark-spam')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </template>
        {{ t('asset_table.mark_spam') }}
      </RuiButton>
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
