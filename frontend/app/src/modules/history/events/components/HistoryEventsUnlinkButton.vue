<script setup lang="ts">
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/**
 * The unlink button on a matched group's header. It asks `question` beside itself, so `confirm`
 * means the user accepted; its clicks stay out of the header, which collapses on click.
 */
defineProps<{
  question: HistoryEventQuestion;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { isMdAndUp } = useBreakpoint();
</script>

<template>
  <span
    class="contents"
    @click.stop
  >
    <ConfirmPopover
      class="shrink-0"
      tone="warning"
      :title="question.title"
      :message="question.message"
      :confirm-label="question.confirmLabel ?? t('transactions.events.actions.unlink')"
      @confirm="emit('confirm')"
    >
      <template #activator="{ attrs }">
        <RuiTooltip
          :open-delay="200"
          :disabled="isMdAndUp"
        >
          <template #activator>
            <RuiButton
              data-testid="collapse-unlink"
              class="h-6! [&>span]:hidden! md:[&>span]:inline!"
              :aria-label="t('transactions.events.actions.unlink')"
              variant="text"
              size="sm"
              color="warning"
              v-bind="attrs"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-unlink"
                  size="14"
                />
              </template>
              {{ t('transactions.events.actions.unlink') }}
            </RuiButton>
          </template>
          {{ t('transactions.events.actions.unlink') }}
        </RuiTooltip>
      </template>
    </ConfirmPopover>
  </span>
</template>
