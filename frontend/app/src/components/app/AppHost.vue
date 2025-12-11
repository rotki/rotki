<script setup lang="ts">
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { useBackendManagement } from '@/composables/backend';
import { useSessionStateCleaner } from '@/composables/session/logout';
import { useLocale } from '@/composables/session/use-locale';
import { useThemeChecker } from '@/modules/theme/use-theme-checker';
import { useSessionSettingsStore } from '@/store/settings/session';

useThemeChecker();

const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const { setupBackend } = useBackendManagement();
const route = useRoute();
useSessionStateCleaner();

const isDevelopment = checkIfDevelopment();
const isPlayground = computed(() => isDevelopment && get(route).path === '/playground');

const { adaptiveLanguage, setLanguage } = useLocale();

onBeforeMount(() => {
  startPromise(setupBackend());
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
    class="overflow-hidden !text-rui-text bg-rui-grey-50 dark:bg-[#121212]"
    :class="{ 'animations-disabled': !animationsEnabled }"
  >
    <slot />
  </div>
  <DevApp v-else />
</template>
