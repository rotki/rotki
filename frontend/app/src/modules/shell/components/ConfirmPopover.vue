<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { nextTick, useTemplateRef } from 'vue';
import { focusFirstControl } from '@/modules/shell/components/focus-first-control';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

/**
 * Asks before an action, anchored to the button that starts it.
 *
 * @remarks
 * For a standalone button, or a place too narrow for an inline strip such as a table's action
 * column. The activator slot gets the menu's `attrs` to bind on its button; `confirm` is emitted
 * only once the user accepts, and the popover closes either way.
 *
 * The menu's own focus handling is off: it would move focus from the question's Cancel onto its
 * container as it opens, and back to the activator on any close, including a click elsewhere on
 * the page. Instead Cancel keeps the focus it takes, and an answer (accept, cancel, Escape) returns
 * focus to the activator, while a click elsewhere leaves it where the user clicked.
 */
defineProps<{
  question: ConfirmQuestion;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

defineSlots<{
  activator: (props: { attrs: Record<string, unknown> }) => any;
}>();

const open = ref<boolean>(false);

const activator = useTemplateRef<HTMLElement>('activator');

async function answer(accepted: boolean): Promise<void> {
  set(open, false);
  if (accepted)
    emit('confirm');
  await nextTick();
  focusFirstControl(get(activator));
}
</script>

<template>
  <RuiMenu
    v-model="open"
    lazy
    disable-auto-focus
    role="dialog"
    :class-names="{ menu: 'w-72' }"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <span
        ref="activator"
        class="contents"
      >
        <slot
          name="activator"
          :attrs="attrs"
        />
      </span>
    </template>
    <InlineConfirm
      layout="panel"
      :question="question"
      @cancel="answer(false)"
      @confirm="answer(true)"
    />
  </RuiMenu>
</template>
