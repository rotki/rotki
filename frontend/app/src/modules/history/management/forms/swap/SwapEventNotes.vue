<script lang="ts" setup>
import type { SwapFeeState } from '@/modules/history/management/forms/swap-event-form';

const spendNotes = defineModel<string>('spendNotes', { required: true });
const receiveNotes = defineModel<string>('receiveNotes', { required: true });

/**
 * The fee rows themselves, so each note is edited on the fee it belongs to. The payload still sends
 * one flat array, but assembling it is the transform's job, not this component's.
 */
const fees = defineModel<SwapFeeState[]>('fees', { required: true });

defineProps<{
  errorMessages: string[];
}>();

const emit = defineEmits<{
  blur: [];
}>();

const { t } = useI18n({ useScope: 'global' });

function feeLabel(index: number): string {
  return get(fees).length > 1
    ? t('swap_event_form.fee_notes_indexed', { index: index + 1 })
    : t('swap_event_form.fee_notes');
}
</script>

<template>
  <RuiAccordions>
    <RuiAccordion
      data-testid="advanced-accordion"
      header-class="py-4"
      eager
    >
      <template #header>
        {{ t('transactions.events.form.advanced') }}
      </template>

      <div class="py-2">
        <RuiTextArea
          v-model="spendNotes"
          prepend-icon="lu-sticky-note"
          data-testid="spend-notes"
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
          v-model="receiveNotes"
          prepend-icon="lu-sticky-note"
          data-testid="receive-notes"
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
          v-for="(fee, index) in fees"
          :key="index"
          v-model="fee.userNotes"
          prepend-icon="lu-sticky-note"
          :data-testid="`fee-notes-${index + 1}`"
          variant="outlined"
          color="primary"
          max-rows="5"
          min-rows="3"
          auto-grow
          :label="feeLabel(index)"
          :error-messages="errorMessages"
          @blur="emit('blur')"
        />
      </div>
    </RuiAccordion>
  </RuiAccordions>
</template>
