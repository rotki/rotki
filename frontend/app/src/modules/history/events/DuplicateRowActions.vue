<script setup lang="ts">
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import { DuplicatesAction, useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/** Each action asks beside its button, so `fix`, `ignore` and `restore` mean the user accepted. */
const { fixLoading, ignoreLoading, mode } = defineProps<{
  mode: 'auto-fix' | 'manual-review' | 'ignored';
  fixLoading?: boolean;
  ignoreLoading?: boolean;
}>();

const emit = defineEmits<{
  fix: [];
  ignore: [];
  restore: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { duplicatesQuestion } = useDuplicatesQuestion();

const fixQuestion = computed<HistoryEventQuestion>(() => duplicatesQuestion(DuplicatesAction.FIX, 1));
const ignoreQuestion = computed<HistoryEventQuestion>(() => duplicatesQuestion(DuplicatesAction.MARK_NON_DUPLICATED, 1));
const restoreQuestion = computed<HistoryEventQuestion>(() => duplicatesQuestion(DuplicatesAction.RESTORE, 1));
</script>

<template>
  <div class="flex items-center gap-2">
    <ConfirmPopover
      v-if="mode === 'auto-fix'"
      tone="warning"
      :title="fixQuestion.title"
      :message="fixQuestion.message"
      :confirm-label="t('customized_event_duplicates.actions.fix')"
      @confirm="emit('fix')"
    >
      <template #activator="{ attrs }">
        <RuiButton
          size="sm"
          color="primary"
          :loading="fixLoading"
          data-testid="duplicate-row-fix"
          v-bind="attrs"
        >
          <template #prepend>
            <RuiIcon
              size="16"
              name="lu-wand-sparkles"
            />
          </template>
          {{ t('customized_event_duplicates.actions.fix') }}
        </RuiButton>
      </template>
    </ConfirmPopover>
    <ConfirmPopover
      v-if="mode === 'ignored'"
      tone="warning"
      :title="restoreQuestion.title"
      :message="restoreQuestion.message"
      :confirm-label="t('customized_event_duplicates.actions.restore')"
      @confirm="emit('restore')"
    >
      <template #activator="{ attrs }">
        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              size="sm"
              color="primary"
              :loading="ignoreLoading"
              data-testid="duplicate-row-restore"
              v-bind="attrs"
            >
              <template #prepend>
                <RuiIcon
                  size="16"
                  name="lu-rotate-ccw"
                />
              </template>
              {{ t('customized_event_duplicates.actions.restore') }}
            </RuiButton>
          </template>
          {{ t('customized_event_duplicates.actions.restore_tooltip') }}
        </RuiTooltip>
      </template>
    </ConfirmPopover>
    <ConfirmPopover
      v-else
      tone="warning"
      :title="ignoreQuestion.title"
      :message="ignoreQuestion.message"
      :confirm-label="t('customized_event_duplicates.actions.mark_non_duplicated')"
      @confirm="emit('ignore')"
    >
      <template #activator="{ attrs }">
        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              size="sm"
              variant="outlined"
              :loading="ignoreLoading"
              data-testid="duplicate-row-ignore"
              v-bind="attrs"
            >
              <template #prepend>
                <RuiIcon
                  size="16"
                  name="lu-eye-off"
                />
              </template>
              {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
            </RuiButton>
          </template>
          {{ t('customized_event_duplicates.actions.mark_non_duplicated_tooltip') }}
        </RuiTooltip>
      </template>
    </ConfirmPopover>
  </div>
</template>
