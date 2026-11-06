<script setup lang="ts">
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

/**
 * A service card's delete button, which asks in its own place before it removes anything.
 *
 * @remarks
 * Sits in the card dialog's left buttons, so the question appears where the user pressed, inside
 * the dialog, instead of in a second dialog over it. `confirm` means the user accepted.
 */
const { disabled = false } = defineProps<{
  label: string;
  title: string;
  message: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

const asking = ref<boolean>(false);

function accept(): void {
  set(asking, false);
  emit('confirm');
}
</script>

<template>
  <InlineConfirm
    v-if="asking"
    class="grow"
    tone="error"
    :title="title"
    :message="message"
    :confirm-label="label"
    data-testid="delete-confirm"
    @cancel="asking = false"
    @confirm="accept()"
  />
  <RuiButton
    v-else
    :disabled="disabled"
    color="error"
    variant="text"
    data-testid="delete-button"
    @click="asking = true"
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
