<script setup lang="ts">
const { isPackaged } = useInterop();
</script>

<template>
  <div>
    <OnboardingSettingsButton v-if="isPackaged" />
    <AboutButton v-else />
  </div>
</template>
