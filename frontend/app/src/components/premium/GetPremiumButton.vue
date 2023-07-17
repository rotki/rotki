<script setup lang="ts">
const { t } = useI18n();
const premium = usePremium();

const { mobile } = useDisplay();
const { isPackaged, premiumURL, navigateToPremium } = useInterop();
</script>

<template>
  <div v-if="!premium" class="mr-2">
    <VTooltip bottom :disabled="!mobile">
      <template #activator="{ on }">
        <VBtn
          data-cy="get-premium-button"
          color="warning"
          rounded
          :fab="mobile"
          small
          class="py-4"
          depressed
          target="_blank"
          :href="isPackaged ? undefined : premiumURL"
          v-on="on"
          @click="isPackaged ? navigateToPremium() : undefined"
        >
          <span v-if="!mobile" class="mr-2">
            {{ t('premium_settings.get') }}
          </span>
          <VIcon>mdi-crown-outline</VIcon>
        </VBtn>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </VTooltip>
  </div>
</template>
