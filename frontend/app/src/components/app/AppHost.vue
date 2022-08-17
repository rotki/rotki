<template>
  <v-app
    v-if="!isPlayground"
    id="rotki"
    :key="language"
    class="app"
    :class="{ ['app--animations-disabled']: !animationsEnabled }"
  >
    <slot />
  </v-app>
  <dev-app v-else />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useRoute } from '@/composables/common';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { checkIfDevelopment } from '@/utils/env-utils';

const DevApp = defineAsyncComponent(() => import('@/DevApp.vue'));

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const { language } = storeToRefs(useFrontendSettingsStore());
const route = useRoute();

const isDevelopment = checkIfDevelopment();
const isPlayground = computed(() => {
  return isDevelopment && get(route).name === 'playground';
});
</script>

<style scoped lang="scss">
.app {
  overflow: hidden;

  &--animations-disabled {
    ::v-deep {
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
