<script setup lang="ts">
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

/**
 * Asks before an action, anchored to the button that starts it.
 *
 * @remarks
 * For places too narrow for an inline strip, such as a table's action column. The activator slot
 * gets the menu's `attrs` to bind on its button; `confirm` is emitted only once the user accepts,
 * and the popover closes either way.
 */
const { tone = 'error' } = defineProps<{
  message: string;
  confirmLabel: string;
  title?: string;
  tone?: 'warning' | 'error';
}>();

const emit = defineEmits<{
  confirm: [];
}>();

defineSlots<{
  activator: (props: { attrs: Record<string, unknown> }) => any;
}>();

const open = ref<boolean>(false);

function accept(): void {
  set(open, false);
  emit('confirm');
}
</script>

<template>
  <RuiMenu
    v-model="open"
    lazy
    role="dialog"
    :class-names="{ menu: 'w-72' }"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <slot
        name="activator"
        :attrs="attrs"
      />
    </template>
    <InlineConfirm
      layout="panel"
      :title="title"
      :message="message"
      :confirm-label="confirmLabel"
      :tone="tone"
      @cancel="open = false"
      @confirm="accept()"
    />
  </RuiMenu>
</template>
