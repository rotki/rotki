<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';
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

const questions = useDuplicatesQuestion();

const fixQuestion = computed<ConfirmQuestion>(() => questions.fixQuestion(1));
const ignoreQuestion = computed<ConfirmQuestion>(() => questions.markNonDuplicatedQuestion(1));
</script>

<template>
  <ConfirmPopover
    v-if="isAutoFixable"
    :question="fixQuestion"
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
    :question="ignoreQuestion"
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
