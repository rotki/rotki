<template>
  <div
    v-if="$slots.title || $slots.subtitle"
    class="flex py-6 gap-4 md:gap-8 lg:gap-12 border-b border-default"
  >
    <div class="w-[150px] lg:w-[288px]">
      <div
        v-if="$slots.title"
        class="font-medium"
      >
        <slot name="title" />
      </div>
      <div
        v-if="$slots.subtitle"
        class="text-rui-text-secondary text-sm"
      >
        <slot name="subtitle" />
      </div>
    </div>
    <div class="flex-1">
      <slot />
    </div>
  </div>
  <slot v-else />
</template>
