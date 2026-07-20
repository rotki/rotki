<script setup lang="ts">
import WelcomeMessageDisplay from '@/modules/auth/login/WelcomeMessageDisplay.vue';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';

const { loading } = defineProps<{
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const dialog = ref<boolean>(false);

const { activeWelcomeMessages, welcomeMessage } = useDynamicMessages();
</script>

<template>
  <RuiDialog
    v-if="welcomeMessage && welcomeMessage.action"
    v-model="dialog"
    max-width="400"
  >
    <template #activator="{ attrs }">
      <RuiButton
        color="primary"
        class="lg:hidden w-full"
        size="lg"
        :disabled="loading"
        variant="outlined"
        type="button"
        data-cy="show-dynamic-messages"
        v-bind="attrs"
      >
        {{ welcomeMessage.action.text }}
      </RuiButton>
    </template>

    <RuiCard>
      <WelcomeMessageDisplay
        class="!bg-transparent !p-0"
        :messages="activeWelcomeMessages"
      />

      <template #footer>
        <div class="w-full" />
        <RuiButton
          color="primary"
          variant="text"
          @click="dialog = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
