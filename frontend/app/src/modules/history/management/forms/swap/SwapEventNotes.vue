<script lang="ts" setup>
import type { SwapEventUserNotes } from '@/types/history/events/schemas';

const userNotes = defineModel<SwapEventUserNotes>({ required: true });

// Array indices: [0] = spend, [1] = receive, [2+] = fee(s)

defineProps<{
  errorMessages: string[];
  feeCount: number;
}>();

const emit = defineEmits<{
  blur: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAccordions>
    <RuiAccordion
      data-cy="advanced-accordion"
      header-class="py-4"
      eager
    >
      <template #header>
        {{ t('transactions.events.form.advanced') }}
      </template>

      <div class="py-2">
        <RuiTextArea
          v-model="userNotes[0]"
          prepend-icon="lu-sticky-note"
          data-cy="spend-notes"
          variant="outlined"
          color="primary"
          max-rows="5"
          min-rows="3"
          auto-grow
          :label="t('swap_event_form.spend_notes')"
          :error-messages="errorMessages"
          @blur="emit('blur')"
        />
        <RuiTextArea
          v-model="userNotes[1]"
          prepend-icon="lu-sticky-note"
          data-cy="receive-notes"
          variant="outlined"
          color="primary"
          max-rows="5"
          min-rows="3"
          auto-grow
          :label="t('swap_event_form.receive_notes')"
          :error-messages="errorMessages"
          @blur="emit('blur')"
        />
        <RuiTextArea
          v-for="feeIndex in feeCount"
          :key="`fee-${feeIndex}`"
          v-model="userNotes[1 + feeIndex]"
          prepend-icon="lu-sticky-note"
          :data-cy="`fee-notes-${feeIndex}`"
          variant="outlined"
          color="primary"
          max-rows="5"
          min-rows="3"
          auto-grow
          :label="feeCount > 1 ? t('swap_event_form.fee_notes_indexed', { index: feeIndex }) : t('swap_event_form.fee_notes')"
          :error-messages="errorMessages"
          @blur="emit('blur')"
        />
      </div>
    </RuiAccordion>
  </RuiAccordions>
</template>
