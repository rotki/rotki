<template>
  <div :class="$style.overlay">
    <div :class="$style.overlay__scroll">
      <RouterView />
    </div>
  </div>
</template>

<style lang="scss" module>
.overlay {
  @apply block overflow-auto lg:overflow-hidden w-full lg:h-screen min-h-screen fixed top-0 bottom-0;

  &__scroll {
    @apply flex flex-col-reverse lg:flex-row w-full lg:h-screen min-h-screen;
  }
}
</style>
