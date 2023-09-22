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
        <RuiButton
          data-cy="get-premium-button"
          color="accent"
          rounded
          size="sm"
          class="py-4"
          target="_blank"
          :href="isPackaged ? undefined : premiumURL"
          v-on="on"
          @click="isPackaged ? navigateToPremium() : undefined"
        >
          <span v-if="!mobile" class="mr-2">
            {{ t('premium_settings.get') }}
          </span>
          <RuiIcon name="vip-crown-line" />
        </RuiButton>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </VTooltip>
  </div>
</template>
