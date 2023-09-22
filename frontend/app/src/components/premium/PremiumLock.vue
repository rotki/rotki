<script setup lang="ts">
const { t } = useI18n();
const { isPackaged, premiumURL, navigateToPremium } = useInterop();
</script>

<template>
  <VTooltip top>
    <template #activator="{ on }">
      <RuiButton
        variant="text"
        icon
        target="_blank"
        v-bind="$attrs"
        :href="isPackaged ? undefined : premiumURL"
        v-on="on"
        @click="isPackaged ? navigateToPremium() : undefined"
      >
        <VIcon>mdi-lock</VIcon>
      </RuiButton>
    </template>
    <span v-text="t('premium_lock.tooltip')" />
  </VTooltip>
</template>
