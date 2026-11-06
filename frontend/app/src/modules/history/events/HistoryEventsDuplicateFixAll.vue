<script setup lang="ts">
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/** The duplicate chip's fix-all link. It asks `question` beside itself, so `confirm` means accepted. */
const { loading = false } = defineProps<{
  question: HistoryEventQuestion;
  loading?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ConfirmPopover
    tone="warning"
    :title="question.title"
    :message="question.message"
    :confirm-label="question.confirmLabel ?? t('common.actions.confirm')"
    @confirm="emit('confirm')"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="link"
        class="underline"
        color="primary"
        :loading="loading"
        data-testid="duplicate-fix-all"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon
            name="lu-wand-sparkles"
            size="10"
          />
        </template>
        {{ t('customized_event_duplicates.actions.fix_all_shown') }}
      </RuiButton>
    </template>
  </ConfirmPopover>
</template>
