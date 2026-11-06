<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import ConfirmInPlace from '@/modules/shell/components/ConfirmInPlace.vue';

/**
 * A service card's delete button, which asks in its own place before it removes anything.
 *
 * @remarks
 * Sits in the card dialog's left buttons, so the question appears where the user pressed, inside
 * the dialog, instead of in a second dialog over it. `confirm` means the user accepted.
 */
const { disabled = false, label, message, title } = defineProps<{
  label: string;
  title: string;
  message: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

const question = computed<ConfirmQuestion>(() => ({ confirmLabel: label, message, title, tone: 'error' }));
</script>

<template>
  <ConfirmInPlace
    class="grow"
    :question="question"
    data-testid="delete-confirm"
    @confirm="emit('confirm')"
  >
    <template #activator="{ ask }">
      <RuiButton
        :disabled="disabled"
        color="error"
        variant="text"
        data-testid="delete-button"
        @click="ask()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </template>
        {{ label }}
      </RuiButton>
    </template>
  </ConfirmInPlace>
</template>
