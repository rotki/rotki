<script setup lang="ts">
const { t } = useI18n();
const { closeApp } = useInterop();
</script>

<template>
  <error-screen
    class="macos-unsupported"
    :header="t('macos_unsupported.header')"
    :alternative="t('macos_unsupported.message')"
  >
    <v-btn depressed color="primary" @click="closeApp()">
      {{ t('common.actions.terminate') }}
    </v-btn>
  </error-screen>
</template>

<style scoped lang="scss">
.macos-unsupported {
  padding: 2rem 0;
  background-color: white;
}
</style>
