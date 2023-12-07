<script setup lang="ts">
import { type ButtonProps } from '@rotki/ui-library-compat';

withDefaults(
  defineProps<{
    tooltip: string;
    onMenu?: object;
    retainFocusOnClick?: boolean;
    className?: string;
    href?: string;
    variant?: ButtonProps['variant'];
    size?: ButtonProps['size'];
  }>(),
  {
    onMenu: undefined,
    retainFocusOnClick: false,
    className: '',
    variant: 'text',
    size: undefined,
    href: undefined
  }
);

const emit = defineEmits<{
  (e: 'click'): void;
}>();

const click = () => emit('click');
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'bottom' }"
    :open-delay="250"
    :close-delay="0"
  >
    <template #activator>
      <RuiButton
        :variant="variant"
        icon
        :href="href"
        :tag="href ? 'a' : 'button'"
        target="_blank"
        :class="[className, !size && '!w-12 !h-12']"
        :size="size"
        :retain-focus-on-click="retainFocusOnClick"
        @click="click()"
        v-on="onMenu"
      >
        <slot />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
