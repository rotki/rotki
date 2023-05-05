<script setup lang="ts">
const { tc } = useI18n();
const { closeApp } = useInterop();
</script>

<template>
  <error-screen
    class="macos-unsupported"
    :header="tc('macos_unsupported.header')"
    :alternative="tc('macos_unsupported.message')"
  >
    <v-btn depressed color="primary" @click="closeApp()">
      {{ tc('common.actions.terminate') }}
    </v-btn>
  </error-screen>
</template>

<style scoped lang="scss">
.macos-unsupported {
  padding: 2rem 0;
  background-color: white;
}
</style>
