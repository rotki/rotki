<script setup lang="ts">
import type { ButtonProps, RuiButton } from '@rotki/ui-library';

import type { ForwardedProps } from '@/modules/core/common/forwarded-props';

interface Props {
  tooltip: string;
  className?: string;
  href?: string;
  variant?: ButtonProps['variant'];
  size?: ButtonProps['size'];
  customColor?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const { tooltip, className = '', href, variant = 'text', size, customColor = false } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiButton, Props>>();

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'bottom' }"
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
        :class="[className, !size && 'w-12! h-12!', !customColor && 'text-rui-text-secondary!']"
        :size="size"
        v-bind="$attrs"
      >
        <slot />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
