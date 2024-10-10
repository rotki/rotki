<template>
  <div>
    <div class="pb-5 border-b border-default">
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

    <slot />
  </div>
</template>
