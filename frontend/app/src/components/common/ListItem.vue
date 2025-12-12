<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg';
    title?: string;
    subtitle?: string;
    noPadding?: boolean;
    noHover?: boolean;
    loading?: boolean;
  }>(),
  {
    loading: false,
    noHover: false,
    noPadding: false,
    size: 'sm',
    subtitle: '',
    title: '',
  },
);

defineSlots<{
  default: () => any;
  avatar: () => any;
  title: () => any;
  subtitle: () => any;
}>();

const avatarSizeClasses = computed(() => {
  if (props.size === 'md')
    return 'w-10 h-10';
  else if (props.size === 'lg')
    return 'w-12 h-12';

  return 'w-8 h-8';
});
</script>

<template>
  <div
    class="flex items-center py-2 gap-2 cursor-pointer"
    :class="[
      {
        '!px-4': !noPadding,
        'hover:bg-rui-grey-100 hover:dark:bg-rui-grey-800': !noHover,
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
    <div class="flex-1 flex flex-col text-truncate leading-[1.25em]">
      <template v-if="loading">
        <RuiSkeletonLoader class="mt-[3px] mb-1.5 w-8" />
        <RuiSkeletonLoader class="w-16 mb-0.5 h-3" />
      </template>
      <template v-else>
        <slot>
          <div
            class="font-medium text-truncate text-sm"
            :title="title"
            data-cy="list-title"
          >
            <slot name="title">
              {{ title }}
            </slot>
          </div>
          <div
            class="text-rui-text-secondary text-caption text-truncate"
            :title="subtitle"
            data-cy="list-subtitle"
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
