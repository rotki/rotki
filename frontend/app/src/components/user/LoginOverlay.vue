<script setup lang="ts">
const isTest = !!import.meta.env.VITE_TEST;
const css = useCssModule();
const { currentBreakpoint } = useTheme();
const { animationEnabled } = useAnimation();

const xsOnly = computed(() => get(currentBreakpoint).xsOnly);
</script>

<template>
  <v-overlay :dark="false" opacity="1" color="grey lighten-4">
    <div
      class="animate"
      :class="{
        [css.loading]: !xsOnly && !isTest,
        [css['loading--paused']]: !animationEnabled
      }"
      data-cy="account-management__loading"
    />
    <slot />
  </v-overlay>
</template>

<style module lang="scss">
@keyframes scrollLarge {
  0% {
    transform: rotate(-13deg) translateY(0px);
  }

  100% {
    transform: rotate(-13deg) translateY(-600px);
  }
}

:global {
  .v-overlay {
    &__content {
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: center;
      height: 100%;
      width: 100%;
    }
  }
}

.loading {
  position: absolute;
  height: calc(100% + 1100px);
  width: calc(100% + 900px);
  left: -450px !important;
  top: -250px !important;
  opacity: 0.5;
  background: url(/assets/images/rotkipattern2.svg) repeat;
  background-size: 450px 150px;
  filter: grayscale(0.5);
  -webkit-animation-name: scrollLarge;
  animation-name: scrollLarge;
  -webkit-animation-duration: 35s;
  animation-duration: 35s;
  -webkit-animation-timing-function: linear;
  animation-timing-function: linear;
  -webkit-animation-iteration-count: infinite;
  animation-iteration-count: infinite;

  &--paused {
    animation-play-state: paused;
  }
}
</style>
