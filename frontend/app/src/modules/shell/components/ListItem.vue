<script setup lang="ts">
const { size = 'sm', title = '', subtitle = '', noPadding = false, noHover = false, loading = false, blurContent = false, inline = false } = defineProps<{
  size?: 'sm' | 'md' | 'lg';
  /** Title and subtitle on one line, for rows that must stay a single line tall. */
  inline?: boolean;
  title?: string;
  subtitle?: string;
  noPadding?: boolean;
  noHover?: boolean;
  loading?: boolean;
  blurContent?: boolean;
}>();

defineSlots<{
  default: () => any;
  avatar: () => any;
  title: () => any;
  subtitle: () => any;
}>();

const avatarSizeClasses = computed<string>(() => {
  if (inline)
    return 'w-6 h-6';
  else if (size === 'md')
    return 'w-10 h-10';
  else if (size === 'lg')
    return 'w-12 h-12';

  return 'w-8 h-8';
});
</script>

<template>
  <div
    class="flex items-center gap-2 cursor-pointer"
    :class="[
      inline ? 'py-0.5' : 'py-2',
      {
        'px-4!': !noPadding,
        'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800': !noHover,
      },
    ]"
  >
    <div
      v-if="$slots.avatar"
      :class="avatarSizeClasses"
      class="flex items-center justify-center avatar shrink-0"
    >
      <slot
        v-if="!loading"
        name="avatar"
      />
      <RuiSkeletonLoader
        v-else
        class="w-full h-full rounded-full"
      />
    </div>
    <div
      class="flex-1 flex text-truncate leading-[1.25em]"
      :class="{ 'blur': blurContent, 'flex-col': !inline, 'items-baseline gap-1.5': inline }"
    >
      <template v-if="loading">
        <RuiSkeletonLoader class="mt-[3px] mb-1.5 w-8" />
        <RuiSkeletonLoader class="w-16 mb-0.5 h-3" />
      </template>
      <template v-else>
        <slot>
          <div
            class="font-medium text-truncate text-sm"
            :title="title"
            data-testid="list-title"
          >
            <slot name="title">
              {{ title }}
            </slot>
          </div>
          <div
            class="text-rui-text-secondary text-caption text-truncate"
            :title="subtitle"
            data-testid="list-subtitle"
          >
            <slot name="subtitle">
              {{ subtitle }}
            </slot>
          </div>
        </slot>
      </template>
    </div>
  </div>
</template>
