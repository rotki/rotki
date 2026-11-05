<script setup lang="ts">
import type { RuiMenu } from '@rotki/ui-library';

import type { ForwardedProps } from '@/modules/core/common/forwarded-props';

interface Props {
  /** A short heading over the explanation; most hints are a sentence or two and go without. */
  title?: string;
}

defineOptions({
  inheritAttrs: false,
});

const { title } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiMenu, Props>>();

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <RuiMenu
    :class-names="{ menu: 'max-w-80' }"
    v-bind="$attrs"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        class="text-rui-text-secondary!"
        v-bind="attrs"
      >
        <RuiIcon name="lu-circle-question-mark" />
      </RuiButton>
    </template>
    <div class="flex flex-col gap-1 px-4 py-3">
      <div
        v-if="title"
        class="text-sm font-semibold text-rui-text"
      >
        {{ title }}
      </div>
      <div class="text-sm leading-relaxed text-rui-text-secondary">
        <slot />
      </div>
    </div>
  </RuiMenu>
</template>
