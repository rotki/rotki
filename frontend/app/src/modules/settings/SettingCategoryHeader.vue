<template>
  <div class="flex flex-col gap-1 min-w-0 border-rui-divider">
    <h3 class="text-base font-semibold text-rui-text">
      <slot name="title" />
    </h3>
    <div
      v-if="$slots.subtitle"
      class="text-sm text-rui-text-secondary"
    >
      <slot name="subtitle" />
    </div>
  </div>
</template>
