<template>
  <v-tooltip top>
    <template #activator="{ on }">
      <v-btn
        text
        icon
        target="_blank"
        v-bind="$attrs"
        :href="interop.isPackaged ? undefined : interop.premiumURL"
        v-on="on"
        @click="interop.isPackaged ? interop.navigateToPremium() : undefined"
      >
        <v-icon>mdi-lock</v-icon>
      </v-btn>
    </template>
    <span v-text="t('premium_lock.tooltip')" />
  </v-tooltip>
</template>
<script setup lang="ts">
import { interop } from '@/electron-interop';

const { t } = useI18n();
</script>
