<script setup lang="ts">
const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const route = useRoute();

const isDevelopment = checkIfDevelopment();
const isPlayground = computed(
  () => isDevelopment && get(route).name === 'playground',
);

const { locale } = useI18nLocale();

const { adaptiveLanguage } = storeToRefs(useSessionStore());

onBeforeMount(() => {
  setLanguage(get(adaptiveLanguage));
});

function setLanguage(language: string) {
  if (language !== get(locale))
    set(locale, language);
}

watch(adaptiveLanguage, (language) => {
  setLanguage(language);
});
</script>

<template>
  <VApp
    v-if="!isPlayground"
    id="rotki"
    :key="adaptiveLanguage"
    class="app"
    :class="{ ['app--animations-disabled']: !animationsEnabled }"
  >
    <slot />
    <AppPremiumManager />
  </VApp>
  <DevApp v-else />
</template>

<style scoped lang="scss">
.app {
  overflow: hidden;

  &--animations-disabled {
    /* stylelint-disable plugin/stylelint-bem-namics */

    :deep(:not(.animate)) {
      // ignore manual animation (e.g. animation on login screen)

      &,
      &::before,
      &::after {
        animation-timing-function: steps(5, end) !important;
      }
    }
    /* stylelint-enable plugin/stylelint-bem-namics */
  }
}
</style>
