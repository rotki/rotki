<script setup lang="ts">
import { type ButtonProps } from '@rotki/ui-library-compat';

defineOptions({
  inheritAttrs: false
});

withDefaults(
  defineProps<{
    tooltip: string;
    retainFocusOnClick?: boolean;
    className?: string;
    href?: string;
    variant?: ButtonProps['variant'];
    size?: ButtonProps['size'];
  }>(),
  {
    retainFocusOnClick: false,
    className: '',
    variant: 'text',
    size: undefined,
    href: undefined
  }
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
        :class="[className, !size && '!w-12 !h-12']"
        :size="size"
        :retain-focus-on-click="retainFocusOnClick"
        v-bind="$attrs"
        v-on="
          // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
          $listeners
        "
      >
        <slot />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
