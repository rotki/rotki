<template>
  <v-app
    v-if="!isPlayground"
    id="rotki"
    :key="adaptiveLanguage"
    class="app"
    :class="{ ['app--animations-disabled']: !animationsEnabled }"
  >
    <slot />
    <app-premium-manager />
  </v-app>
  <dev-app v-else />
</template>

<script setup lang="ts">
import AppPremiumManager from '@/components/app/AppPremiumManager.vue';
import { useSessionStore } from '@/store/session';
import { useSessionSettingsStore } from '@/store/settings/session';
import { checkIfDevelopment } from '@/utils/env-utils';

const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const route = useRoute();

const isDevelopment = checkIfDevelopment();
const isPlayground = computed(() => {
  return isDevelopment && get(route).name === 'playground';
});

const { locale } = useI18n();

const { adaptiveLanguage } = storeToRefs(useSessionStore());

onBeforeMount(() => {
  setLanguage(get(adaptiveLanguage));
});

const setLanguage = (language: string) => {
  if (language !== get(locale)) {
    set(locale, language);
  }
};

watch(adaptiveLanguage, language => {
  setLanguage(language);
});
</script>

<style scoped lang="scss">
.app {
  overflow: hidden;

  &--animations-disabled {
    :deep() {
      * {
        &:not(.animate) {
          // ignore manual animation (e.g. animation on login screen)

          &,
          &::before,
          &::after {
            animation-timing-function: steps(5, end) !important;
          }
        }
      }
    }
  }
}
</style>
