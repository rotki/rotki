<script setup lang="ts">
const { navigateToPremium, premiumURL, isPackaged } = useInterop();
const { navigateToDashboard } = useAppNavigation();

const keyHandler = async (event: KeyboardEvent) => {
  const keys = ['Escape', 'Esc'];
  if (!keys.includes(event.key)) {
    return;
  }
  await navigateToDashboard();
};

onBeforeMount(() => {
  document.addEventListener('keydown', keyHandler);
});

onBeforeUnmount(() => {
  document.removeEventListener('keydown', keyHandler);
});

const { t } = useI18n();
</script>
<template>
  <v-card light max-width="500" class="mx-auto premium-reminder">
    <v-card-title class="premium-reminder__title">
      {{ t('premium_reminder.title') }}
    </v-card-title>
    <v-card-text>
      <v-row class="mx-auto text-justify">
        <v-col cols="auto" align-self="center">
          <v-icon color="success" size="48"> mdi-information </v-icon>
        </v-col>
        <v-col cols="10">{{ t('premium_reminder.description') }}</v-col>
      </v-row>
    </v-card-text>
    <v-card-actions class="pa-4">
      <v-spacer />
      <v-btn
        color="primary"
        class="premium-reminder__buttons__cancel"
        depressed
        outlined
        @click="navigateToDashboard()"
      >
        {{ t('common.actions.close') }}
      </v-btn>
      <v-btn
        color="primary"
        depressed
        target="_blank"
        :href="isPackaged ? undefined : premiumURL"
        class="premium-reminder__buttons__confirm"
        @click="navigateToPremium()"
      >
        {{ t('common.actions.upgrade') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
