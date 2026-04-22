<script setup lang="ts">
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
  <div
    v-if="showSelectionToggle"
    class="flex flex-row gap-3"
  >
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          size="xl"
          :disabled="disabled"
          @click="emit('toggle-mode')"
        >
          <template #prepend>
            <RuiIcon name="lu-copy-check" />
          </template>
        </RuiButton>
      </template>
      <span>{{ selectionMode ? t('account_balances.exit_selection_mode') : t('account_balances.enter_selection_mode') }}</span>
    </RuiTooltip>

    <template v-if="selectionMode">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            class="h-10"
            variant="outlined"
            color="error"
            :disabled="selectedCount === 0"
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
        </template>
        <span>{{ t('ignore_buttons.ignore_tooltip') }}</span>
      </RuiTooltip>
      <div class="border-l border-default pl-3">
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              class="h-10"
              variant="outlined"
              color="error"
              :disabled="selectedCount === 0"
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
          </template>
          <span>{{ t('asset_table.mark_spam_tooltip') }}</span>
        </RuiTooltip>
      </div>
      <div
        v-if="selectedCount > 0"
        class="flex gap-2 items-center text-sm"
      >
        {{ t('asset_table.selected', { count: selectedCount }) }}
        <RuiButton
          size="sm"
          class="!py-0 !px-1.5 !gap-0.5 dark:!bg-opacity-30 dark:!text-white"
          @click="emit('clear-selection')"
        >
          <template #prepend>
            <RuiIcon
              name="lu-x"
              size="14"
            />
          </template>
          {{ t('common.actions.clear_selection') }}
        </RuiButton>
      </div>
    </template>
  </div>
</template>
