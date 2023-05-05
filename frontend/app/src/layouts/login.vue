<script setup lang="ts">
const { showAbout } = storeToRefs(useAreaVisibilityStore());
const { isPackaged } = useInterop();
</script>

<template>
  <app-host>
    <frontend-update-notifier v-if="!isPackaged" />
    <app-messages>
      <login-host />
    </app-messages>
    <v-dialog v-if="showAbout" v-model="showAbout" max-width="500">
      <about />
    </v-dialog>
  </app-host>
</template>
