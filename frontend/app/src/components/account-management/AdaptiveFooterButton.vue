<script setup lang="ts">
import { useInterop } from '@/composables/electron-interop';
import AboutButton from '@/components/account-management/AboutButton.vue';
import OnboardingSettingsButton from '@/components/helper/OnboardingSettingsButton.vue';

const { isPackaged } = useInterop();
</script>

<template>
  <div>
    <OnboardingSettingsButton v-if="isPackaged" />
    <AboutButton v-else />
  </div>
</template>
