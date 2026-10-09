<template>
  <div class="h-13 text-sm flex items-center justify-between px-4">
    <div class="font-medium flex items-center gap-3">
      <slot name="label" />
    </div>
    <div class="font-semibold">
      <slot name="value" />
    </div>
  </div>
</template>
