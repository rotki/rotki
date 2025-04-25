<script lang="ts" setup>
const userNotes = defineModel<[string, string] | [string, string, string]>({ required: true });

defineProps<{
  errorMessages: string[];
  hasFee: boolean;
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
          v-if="hasFee && userNotes.length === 3"
          v-model="userNotes[2]"
          prepend-icon="lu-sticky-note"
          data-cy="fee-notes"
          :disabled="!hasFee"
          variant="outlined"
          color="primary"
          max-rows="5"
          min-rows="3"
          auto-grow
          :label="t('swap_event_form.fee_notes')"
          :error-messages="errorMessages"
          @blur="emit('blur')"
        />
      </div>
    </RuiAccordion>
  </RuiAccordions>
</template>
