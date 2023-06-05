<script setup lang="ts">
const { t } = useI18n();
const premium = usePremium();

const { mobile } = useDisplay();
const { isPackaged, premiumURL, navigateToPremium } = useInterop();
</script>

<template>
  <div v-if="!premium" class="mr-2">
    <v-tooltip bottom :disabled="!mobile">
      <template #activator="{ on }">
        <v-btn
          data-cy="get-premium-button"
          color="warning"
          rounded
          :fab="mobile"
          :small="mobile"
          depressed
          target="_blank"
          :href="isPackaged ? undefined : premiumURL"
          v-on="on"
          @click="isPackaged ? navigateToPremium() : undefined"
        >
          <span v-if="!mobile" class="mr-2">
            {{ t('premium_settings.get') }}
          </span>
          <v-icon>mdi-crown-outline</v-icon>
        </v-btn>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </v-tooltip>
  </div>
</template>
