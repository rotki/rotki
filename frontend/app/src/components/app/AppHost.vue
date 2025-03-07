<script setup lang="ts">
import { useLocale } from '@/composables/session/use-locale';
import { useSessionSettingsStore } from '@/store/settings/session';
import { checkIfDevelopment } from '@shared/utils';

const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const route = useRoute();

const isDevelopment = checkIfDevelopment();
const isPlayground = computed(() => isDevelopment && get(route).path === '/playground');

const { adaptiveLanguage, setLanguage } = useLocale();

onBeforeMount(() => {
  setLanguage(get(adaptiveLanguage));
});

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
