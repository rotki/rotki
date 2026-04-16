<script setup lang="ts">
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { useSigil } from '@/modules/core/sigil/use-sigil';
import { useLocale } from '@/modules/session/use-locale';
import { useSessionStateCleaner } from '@/modules/session/use-session-state-cleaner';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useThemeChecker } from '@/modules/shell/theme/use-theme-checker';

useThemeChecker();
useSigil();

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
  startPromise(setLanguage(get(adaptiveLanguage)));
});

watch(adaptiveLanguage, async (language) => {
  await setLanguage(language);
});
</script>

<template>
  <div
    v-if="!isPlayground"
    id="rotki"
    class="overflow-hidden !text-rui-text bg-rui-grey-50 dark:bg-dark-surface"
    :class="{ 'animations-disabled': !animationsEnabled }"
  >
    <slot />
  </div>
  <DevApp v-else />
</template>
