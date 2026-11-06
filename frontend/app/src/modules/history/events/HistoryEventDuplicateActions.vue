<script setup lang="ts">
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import { DuplicatesAction, useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/**
 * A duplicate group's own fix and mark-non-duplicated buttons on its history row. Each asks beside
 * itself, so `fix` and `ignore` mean the user accepted.
 */
const { fixLoading = false, ignoreLoading = false, isAutoFixable = false, isDuplicate = false } = defineProps<{
  isAutoFixable?: boolean;
  isDuplicate?: boolean;
  fixLoading?: boolean;
  ignoreLoading?: boolean;
}>();

const emit = defineEmits<{
  fix: [];
  ignore: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { duplicatesQuestion } = useDuplicatesQuestion();

const fixQuestion = computed<HistoryEventQuestion>(() => duplicatesQuestion(DuplicatesAction.FIX, 1));
const ignoreQuestion = computed<HistoryEventQuestion>(() => duplicatesQuestion(DuplicatesAction.MARK_NON_DUPLICATED, 1));
</script>

<template>
  <ConfirmPopover
    v-if="isAutoFixable"
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
        class="mr-1"
        :loading="fixLoading"
        data-testid="event-fix-duplicate"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon
            name="lu-wand-sparkles"
            size="16"
          />
        </template>
        {{ t('customized_event_duplicates.actions.fix') }}
      </RuiButton>
    </template>
  </ConfirmPopover>
  <ConfirmPopover
    v-if="isDuplicate"
    tone="warning"
    :title="ignoreQuestion.title"
    :message="ignoreQuestion.message"
    :confirm-label="t('customized_event_duplicates.actions.mark_non_duplicated')"
    @confirm="emit('ignore')"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        size="sm"
        class="mr-2"
        :loading="ignoreLoading"
        data-testid="event-ignore-duplicate"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon
            name="lu-eye-off"
            size="16"
          />
        </template>
        {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
      </RuiButton>
    </template>
  </ConfirmPopover>
</template>
