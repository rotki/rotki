<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { useTemplateRef } from 'vue';

/**
 * A question asked in place, beside what it concerns, instead of in a dialog over the page.
 *
 * @remarks
 * `strip` is one tinted line for a row or a toolbar; `panel` stacks a title and the message for a
 * menu or a popover, where a line break in `message` is kept so a second paragraph reads as one,
 * and an unbroken run such as a validator public key wraps instead of overflowing.
 * Cancel takes focus when the question appears, so Enter never confirms by accident, and Escape
 * cancels. Dropping the question once it no longer applies (the item went
 * away, the job settled) is the caller's job.
 */
const { cancelLabel, layout = 'strip', loading = false, question } = defineProps<{
  question: ConfirmQuestion;
  cancelLabel?: string;
  layout?: 'strip' | 'panel';
  loading?: boolean;
}>();

const emit = defineEmits<{
  cancel: [];
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const root = useTemplateRef<HTMLElement>('root');

const tone = computed<'warning' | 'error'>(() => question.tone ?? 'warning');

const toneClass = computed<string>(() => get(tone) === 'error'
  ? 'bg-rui-error/10 border-rui-error/40'
  : 'bg-rui-warning/10 border-rui-warning/40');

onMounted(() => {
  get(root)?.querySelector<HTMLButtonElement>('[data-testid=inline-confirm-cancel]')?.focus();
});
</script>

<template>
  <div
    ref="root"
    role="alertdialog"
    :aria-label="question.title ?? question.message"
    data-testid="inline-confirm"
    :class="layout === 'strip'
      ? ['flex items-center gap-2 rounded-sm px-2 py-1 border', toneClass]
      : 'flex flex-col gap-3 p-4'"
    @keydown.esc.stop="emit('cancel')"
  >
    <div
      v-if="layout === 'panel'"
      class="flex flex-col gap-1"
    >
      <p
        v-if="question.title"
        class="text-sm font-medium text-rui-text"
      >
        {{ question.title }}
      </p>
      <p class="text-sm text-rui-text-secondary whitespace-pre-line wrap-anywhere">
        {{ question.message }}
      </p>
    </div>
    <span
      v-else
      class="flex-1 min-w-0 text-caption text-rui-text"
    >
      {{ question.message }}
    </span>
    <div
      class="flex shrink-0 gap-2"
      :class="{ 'justify-end': layout === 'panel' }"
    >
      <RuiButton
        size="sm"
        variant="text"
        :class="{ 'h-6.5! py-0!': layout === 'strip' }"
        data-testid="inline-confirm-cancel"
        @click="emit('cancel')"
      >
        {{ cancelLabel ?? t('common.actions.cancel') }}
      </RuiButton>
      <RuiButton
        size="sm"
        :color="tone"
        :class="{ 'h-6.5! py-0!': layout === 'strip' }"
        :loading="loading"
        data-testid="inline-confirm-accept"
        @click="emit('confirm')"
      >
        {{ question.confirmLabel }}
      </RuiButton>
    </div>
  </div>
</template>
