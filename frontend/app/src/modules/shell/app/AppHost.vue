<script setup lang="ts">
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { useSigil } from '@/modules/core/sigil/use-sigil';
import SingleTabOverlay from '@/modules/session/single-tab/SingleTabOverlay.vue';
import { useSingleTabGuard } from '@/modules/session/single-tab/use-single-tab-guard';
import { useLocale } from '@/modules/session/use-locale';
import { useSessionStateCleaner } from '@/modules/session/use-session-state-cleaner';
import { useSetting } from '@/modules/settings/use-setting';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useThemeChecker } from '@/modules/shell/theme/use-theme-checker';

useThemeChecker();
useSigil();

const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const animationsEnabled = useSetting('animationsEnabled');
const { setupBackend } = useBackendManagement();
const route = useRoute();
useSessionStateCleaner();
useSingleTabGuard();

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
    <SingleTabOverlay />
  </div>
  <DevApp v-else />
</template>
