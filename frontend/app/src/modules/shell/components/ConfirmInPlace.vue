<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { nextTick, useTemplateRef } from 'vue';
import { focusFirstControl } from '@/modules/shell/components/focus-first-control';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

/**
 * A control that turns into its own question when pressed, and back into itself once answered.
 *
 * @remarks
 * The activator slot receives `ask` rather than a click handler to bind, so the caller decides when
 * the question is needed: a link that only asks while a form is dirty calls `ask()` on that branch
 * and acts at once on the other, and an activator wrapped in a tooltip calls it from the button
 * inside without the attributes having to be routed to the right element.
 *
 * Attributes such as `class` and `data-testid` land on the element holding the question, not on
 * the activator, which is the caller's own markup and is styled in the slot.
 *
 * The activator is unmounted while the question shows, so once it is back, after cancel or after
 * accept, focus returns to its first enabled control. An activator the caller removed or disabled on
 * accept is left alone.
 */
defineOptions({
  inheritAttrs: false,
});

const { cancelLabel, question } = defineProps<{
  question: ConfirmQuestion;
  cancelLabel?: string;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

defineSlots<{
  activator: (props: { ask: () => void }) => any;
}>();

const asking = ref<boolean>(false);

const activator = useTemplateRef<HTMLElement>('activator');

function ask(): void {
  set(asking, true);
}

async function answer(accepted: boolean): Promise<void> {
  set(asking, false);
  if (accepted)
    emit('confirm');
  await nextTick();
  focusFirstControl(get(activator));
}
</script>

<template>
  <div
    v-if="asking"
    v-bind="$attrs"
  >
    <InlineConfirm
      :question="question"
      :cancel-label="cancelLabel"
      @cancel="answer(false)"
      @confirm="answer(true)"
    />
  </div>
  <span
    v-else
    ref="activator"
    class="contents"
  >
    <slot
      name="activator"
      :ask="ask"
    />
  </span>
</template>
