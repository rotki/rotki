<script setup lang="ts">
import type { ContextColorsType, RuiButton, RuiIcons } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';

import { type SelectionQuestion, useTableSelectionAsk, useTableSelectionCollapsed } from '@/modules/core/table/table-selection-collapse';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

interface Props {
  icon: RuiIcons;
  color?: ContextColorsType;
  disabled?: boolean;
  loading?: boolean;
  /** Asked before `click` is emitted: beside the button, or inside the bar's menu once collapsed. */
  confirm?: SelectionQuestion;
}

defineOptions({ inheritAttrs: false });

const { color, confirm, disabled = false, loading = false } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiButton, Props, 'click'>>();

const emit = defineEmits<{
  click: [];
}>();

defineSlots<{
  default: () => any;
}>();

const collapsed = useTableSelectionCollapsed();
const askInMenu = useTableSelectionAsk();

/**
 * Runs a menu entry, or hands its question to the bar first.
 *
 * @remarks
 * Stopping the click keeps the bar's menu open, so the question can replace its entries.
 */
function clickMenuEntry(event: MouseEvent): void {
  if (confirm && askInMenu) {
    event.stopPropagation();
    askInMenu(confirm, () => emit('click'));
    return;
  }
  emit('click');
}
</script>

<template>
  <RuiButton
    v-if="collapsed"
    variant="list"
    :color="color"
    :disabled="disabled || loading"
    v-bind="$attrs"
    @click="clickMenuEntry($event)"
  >
    <template #prepend>
      <RuiIcon :name="icon" />
    </template>
    <slot />
  </RuiButton>
  <ConfirmPopover
    v-else-if="confirm"
    :title="confirm.title"
    :message="confirm.message"
    :confirm-label="confirm.confirmLabel"
    @confirm="emit('click')"
  >
    <template #activator="{ attrs }">
      <RuiButton
        size="sm"
        variant="outlined"
        :color="color"
        :disabled="disabled"
        :loading="loading"
        v-bind="{ ...$attrs, ...attrs }"
      >
        <template #prepend>
          <RuiIcon
            :name="icon"
            size="16"
          />
        </template>
        <slot />
      </RuiButton>
    </template>
  </ConfirmPopover>
  <RuiButton
    v-else
    size="sm"
    variant="outlined"
    :color="color"
    :disabled="disabled"
    :loading="loading"
    v-bind="$attrs"
    @click="emit('click')"
  >
    <template #prepend>
      <RuiIcon
        :name="icon"
        size="16"
      />
    </template>
    <slot />
  </RuiButton>
</template>
