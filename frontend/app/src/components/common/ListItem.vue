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
    size: 'sm',
    title: '',
    subtitle: '',
    noPadding: false,
    noHover: false,
    loading: false
  }
);

const avatarSizeClasses = computed(() => {
  if (props.size === 'md') {
    return 'w-10 h-10';
  } else if (props.size === 'lg') {
    return 'w-12 h-12';
  }
  return 'w-8 h-8';
});

const slots = useSlots();

const css = useCssModule();
</script>

<template>
  <div
    :class="[
      css.wrapper,
      {
        [css['with-padding']]: !noPadding,
        'hover:bg-rui-grey-100 hover:dark:bg-rui-grey-800': !noHover
      }
    ]"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <div
      v-if="slots.avatar"
      :class="avatarSizeClasses"
      class="flex items-center justify-center avatar"
    >
      <slot name="avatar" />
    </div>
    <div class="flex-1 flex flex-col text-truncate">
      <template v-if="loading">
        <RuiSkeletonLoader class="mt-[3px] mb-1.5 w-8" />
        <RuiSkeletonLoader class="w-16 mb-1 h-3" />
      </template>
      <template v-else>
        <slot>
          <div
            class="font-medium text-truncate"
            :title="title"
            data-cy="list-title"
          >
            <slot name="title">
              {{ title }}
            </slot>
          </div>
          <div
            class="text-rui-text-secondary text-caption whitespace-nowrap text-truncate"
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

<style lang="scss" module>
.wrapper {
  @apply flex items-center py-2 gap-2 cursor-pointer;

  &.with-padding {
    @apply px-4;
  }
}
</style>
