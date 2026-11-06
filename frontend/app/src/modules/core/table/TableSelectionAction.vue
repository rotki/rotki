<script setup lang="ts">
import type { ContextColorsType, RuiButton, RuiIcons } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { useTableSelectionCollapsed } from '@/modules/core/table/table-selection-collapse';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import { useConfirmMenuAsk } from '@/modules/shell/components/use-confirm-menu';

interface Props {
  icon: RuiIcons;
  color?: ContextColorsType;
  disabled?: boolean;
  loading?: boolean;
  /** Asked before `click` is emitted: beside the button, or inside the bar's menu once collapsed. */
  confirm?: ConfirmQuestion;
}

defineOptions({ inheritAttrs: false });

const { color, confirm, disabled = false, loading = false } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiButton, Props, 'click'>>();

const emit = defineEmits<{
  click: [];
}>();

defineSlots<{
  default: () => any;
}>();

/** The outlined button, bound to the popover's activator `attrs` or, without a question, to a plain click. */
const [DefineButton, ReuseButton] = createReusableTemplate<{ attrs: Record<string, unknown> }>();

const collapsed = useTableSelectionCollapsed();
const askInMenu = useConfirmMenuAsk();

/** Runs a menu entry, or hands its question to the bar's menu first. */
function clickMenuEntry(): void {
  if (confirm && askInMenu)
    askInMenu(confirm, () => emit('click'));
  else
    emit('click');
}
</script>

<template>
  <DefineButton #default="{ attrs }">
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
  </DefineButton>
  <RuiButton
    v-if="collapsed"
    variant="list"
    :color="color"
    :disabled="disabled || loading"
    v-bind="$attrs"
    @click="clickMenuEntry()"
  >
    <template #prepend>
      <RuiIcon :name="icon" />
    </template>
    <slot />
  </RuiButton>
  <ConfirmPopover
    v-else-if="confirm"
    :question="confirm"
    @confirm="emit('click')"
  >
    <template #activator="{ attrs }">
      <ReuseButton :attrs="attrs" />
    </template>
  </ConfirmPopover>
  <ReuseButton
    v-else
    :attrs="{ onClick: () => emit('click') }"
  />
</template>
