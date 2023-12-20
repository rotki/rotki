<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg';
  }>(),
  {
    size: 'sm'
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
</script>

<template>
  <div
    class="flex items-center px-4 py-2 gap-4 hover:bg-rui-grey-100 hover:dark:bg-rui-grey-800 cursor-pointer"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <div v-if="$slots.avatar" :class="avatarSizeClasses" class="flex justify-center">
      <slot name="avatar" />
    </div>
    <div class="flex flex-col">
      <div class="font-semibold">
        <slot name="title" />
      </div>
      <div class="text-rui-text-secondary text-caption">
        <slot />
      </div>
    </div>
  </div>
</template>
