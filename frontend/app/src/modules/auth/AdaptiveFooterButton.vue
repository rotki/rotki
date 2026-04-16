<script setup lang="ts">
import AboutButton from '@/modules/auth/AboutButton.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import OnboardingSettingsButton from '@/modules/shell/components/OnboardingSettingsButton.vue';

const { isPackaged } = useInterop();
</script>

<template>
  <div>
    <OnboardingSettingsButton v-if="isPackaged" />
    <AboutButton v-else />
  </div>
</template>
