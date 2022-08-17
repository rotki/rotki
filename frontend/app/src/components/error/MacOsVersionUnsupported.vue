<template>
  <error-screen
    class="macos-unsupported"
    :header="tc('macos_unsupported.header')"
    :alternative="tc('macos_unsupported.message')"
  >
    <v-btn
      depressed
      color="primary"
      @click="closeApp()"
      v-text="tc('macos_unsupported.terminate')"
    />
  </error-screen>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n-composable';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import { useInterop } from '@/electron-interop';

const { tc } = useI18n();
const { closeApp } = useInterop();
</script>

<style scoped lang="scss">
.macos-unsupported {
  background-color: white;
}
</style>
