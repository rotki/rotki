<script setup lang="ts">
import type { ButtonProps } from '@rotki/ui-library';

defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    tooltip: string;
    retainFocusOnClick?: boolean;
    className?: string;
    href?: string;
    variant?: ButtonProps['variant'];
    size?: ButtonProps['size'];
    customColor?: boolean;
  }>(),
  {
    className: '',
    customColor: false,
    href: undefined,
    retainFocusOnClick: false,
    size: undefined,
    variant: 'text',
  },
);
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
        :class="[className, !size && '!w-12 !h-12', !customColor && '!text-rui-text-secondary']"
        :size="size"
        :retain-focus-on-click="retainFocusOnClick"
        v-bind="$attrs"
      >
        <slot />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
