<script setup lang="ts">
import type { ServerColor } from '@/modules/auth/login/use-custom-backend';

const url = defineModel<string>('url', { required: true });
const sessionOnly = defineModel<boolean>('sessionOnly', { required: true });

const {
  color,
  errorMessages = [],
  loading,
  open,
  saved,
} = defineProps<{
  open: boolean;
  loading: boolean;
  saved: boolean;
  color?: ServerColor;
  errorMessages?: string[];
}>();

const emit = defineEmits<{
  save: [];
  clear: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAccordion :open="open">
    <div
      v-if="open"
      class="flex flex-col justify-stretch space-y-4 pt-4"
    >
      <RuiTextField
        v-model="url"
        color="primary"
        variant="outlined"
        :error-messages="errorMessages"
        :disabled="saved"
        :label="t('login.custom_backend.label')"
        :placeholder="t('login.custom_backend.placeholder')"
        :hint="t('login.custom_backend.hint')"
        class="[&>div]:bg-transparent"
        dense
      >
        <template #prepend>
          <RuiIcon
            name="lu-server"
            :color="color"
          />
        </template>
        <template #append>
          <RuiButton
            v-if="!saved"
            :disabled="loading"
            variant="text"
            class="-mr-1 !p-2"
            type="button"
            icon
            @click="emit('save')"
          >
            <RuiIcon
              name="lu-save"
              color="primary"
              size="20"
            />
          </RuiButton>
          <RuiButton
            v-else
            variant="text"
            class="-mr-1 !p-2"
            type="button"
            icon
            @click="emit('clear')"
          >
            <RuiIcon
              name="lu-trash-2"
              color="primary"
              size="20"
            />
          </RuiButton>
        </template>
      </RuiTextField>

      <RuiCheckbox
        v-model="sessionOnly"
        class="-ml-2"
        color="primary"
        hide-details
        :disabled="saved"
      >
        {{ t('login.custom_backend.session_only') }}
      </RuiCheckbox>
    </div>
  </RuiAccordion>
</template>
