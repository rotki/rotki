<template>
  <div>
    <div class="flex flex-row items-center gap-2">
      <slot name="header" />
    </div>
    <div class="mt-8">
      <slot />
    </div>
  </div>
</template>
