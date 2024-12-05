<script setup lang="ts">
import { checkIfDevelopment } from '@shared/utils';
import { useSessionStore } from '@/store/session';
import { useSessionSettingsStore } from '@/store/settings/session';

const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const route = useRoute();

const isDevelopment = checkIfDevelopment();
const isPlayground = computed(() => isDevelopment && get(route).path === '/playground');

const { locale } = useI18n();

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
  <div
    v-if="!isPlayground"
    id="rotki"
    :key="adaptiveLanguage"
    class="app !text-rui-text bg-rui-grey-50 dark:bg-[#121212]"
    :class="{ ['app--animations-disabled']: !animationsEnabled }"
  >
    <slot />
  </div>
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
