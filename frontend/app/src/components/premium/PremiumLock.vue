<template>
  <v-tooltip top>
    <template #activator="{ on }">
      <v-btn
        text
        icon
        target="_blank"
        v-bind="$attrs"
        :href="isPackaged ? undefined : premiumURL"
        v-on="on"
        @click="isPackaged ? navigateToPremium() : undefined"
      >
        <v-icon>mdi-lock</v-icon>
      </v-btn>
    </template>
    <span v-text="t('premium_lock.tooltip')" />
  </v-tooltip>
</template>
<script setup lang="ts">
const { t } = useI18n();
const { isPackaged, premiumURL, navigateToPremium } = useInterop();
</script>
