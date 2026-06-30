<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import FullSizeContent from '@/modules/shell/components/FullSizeContent.vue';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';

const { full = false, icon, variant = 'default' } = defineProps<{
  full?: boolean;
  /** When set (and no `logo` slot is provided), renders this icon instead of the rotki logo. */
  icon?: RuiIcons;
  /** Tints the circle + icon. `success` signals a healthy/all-clear state. */
  variant?: 'default' | 'success';
}>();

const { isMdAndUp } = useBreakpoint();

const circleClasses = computed<string>(() => {
  if (icon) {
    const tint = variant === 'success'
      ? 'bg-rui-success/10 dark:bg-rui-success/15'
      : 'bg-rui-grey-200 dark:bg-rui-grey-900';
    return `${tint} ${get(isMdAndUp) ? 'size-40' : 'size-32'}`;
  }
  return `bg-rui-grey-200 dark:bg-rui-grey-900 ${get(isMdAndUp) ? 'size-64 p-16' : 'size-48 p-8'}`;
});

const iconColor = computed<'secondary' | 'success'>(() => variant === 'success' ? 'success' : 'secondary');
</script>

<template>
  <FullSizeContent
    class="gap-4"
    :class="{ '!h-auto !mt-20': !full }"
  >
    <div class="flex items-center justify-center mb-8">
      <div
        class="rounded-full flex items-center justify-center"
        :class="circleClasses"
      >
        <slot name="logo">
          <RuiIcon
            v-if="icon"
            :name="icon"
            :size="isMdAndUp ? 64 : 48"
            :color="iconColor"
          />
          <RotkiLogo
            v-else
            :size="isMdAndUp ? 8 : 4"
            unique-key="3"
          />
        </slot>
      </div>
    </div>
    <div
      v-if="$slots.title"
      class="text-h5"
    >
      <slot name="title" />
    </div>
    <div
      v-if="$slots.default"
      class="text-subtitle-2 text-rui-text-secondary max-w-md mx-auto"
    >
      <slot />
    </div>
  </FullSizeContent>
</template>
