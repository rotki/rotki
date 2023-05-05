<script setup lang="ts">
const { navigateToPremium, premiumURL, isPackaged } = useInterop();

const emit = defineEmits<{ (e: 'dismiss'): void }>();

const keyHandler = async (event: KeyboardEvent) => {
  const keys = ['Escape', 'Esc'];
  if (!keys.includes(event.key)) {
    return;
  }
  emit('dismiss');
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
  <card flat data-cy="premium-reminder">
    <template #title>
      {{ t('premium_reminder.title') }}
    </template>
    <v-row class="mx-auto text-justify my-2 text-body-1">
      <v-col cols="auto" align-self="center">
        <v-icon color="success" size="48"> mdi-information </v-icon>
      </v-col>
      <v-col cols="10">{{ t('premium_reminder.description') }}</v-col>
    </v-row>
    <template #buttons>
      <v-spacer />
      <v-btn
        color="primary"
        data-cy="premium-reminder__cancel"
        depressed
        outlined
        @click="emit('dismiss')"
      >
        {{ t('common.actions.close') }}
      </v-btn>
      <v-btn
        color="primary"
        depressed
        target="_blank"
        :href="isPackaged ? undefined : premiumURL"
        data-cy="premium-reminder__confirm"
        @click="navigateToPremium()"
      >
        {{ t('common.actions.upgrade') }}
      </v-btn>
    </template>
  </card>
</template>
