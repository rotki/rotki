<script setup lang="ts">
import { liveSessionKey } from '@/modules/core/session/session-lifecycle';
import AppQuitting from '@/modules/shell/app/AppQuitting.vue';
import { SessionHost } from '@/modules/shell/app/session-host';
import { useAppQuitting } from '@/modules/shell/app/use-app-quitting';
import LayoutWrapper from '@/modules/shell/layout/LayoutWrapper.vue';

const { quitting } = useAppQuitting();
const sessionKey = liveSessionKey();
</script>

<template>
  <AppQuitting v-if="quitting" />
  <LayoutWrapper v-else>
    <RouterView />
  </LayoutWrapper>
  <SessionHost
    v-if="sessionKey"
    :key="sessionKey"
  />
</template>
