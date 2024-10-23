<template>
  <div class="border-default">
    <h6 class="text-h6 font-semibold">
      <slot name="title" />
    </h6>
    <div
      v-if="$slots.subtitle"
      class="text-rui-text-secondary text-sm"
    >
      <slot name="subtitle" />
    </div>
  </div>
</template>
