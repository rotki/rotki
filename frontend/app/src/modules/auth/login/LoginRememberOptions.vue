<script setup lang="ts">
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const rememberUsername = defineModel<boolean>('rememberUsername', { required: true });
const rememberPassword = defineModel<boolean>('rememberPassword', { required: true });

const { disabled, isDocker } = defineProps<{
  disabled: boolean;
  isDocker?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { isPackaged } = useInterop();
</script>

<template>
  <!-- nothing at all in a browser outside docker, so the backend toggle beside it takes the row's start -->
  <div v-if="isDocker || isPackaged">
    <RuiCheckbox
      v-if="isDocker"
      v-model="rememberUsername"
      :disabled="disabled || rememberPassword"
      color="primary"
      hide-details
    >
      {{ t('login.remember_username') }}
    </RuiCheckbox>
    <div
      v-if="isPackaged"
      class="flex items-center justify-between"
    >
      <div>
        <RuiCheckbox
          v-model="rememberPassword"
          :disabled="disabled"
          color="primary"
          hide-details
        >
          {{ t('login.remember_password') }}
        </RuiCheckbox>
      </div>
      <RuiTooltip
        :open-delay="400"
        :close-delay="0"
        class="ml-2"
        :class-names="{ tooltip: 'max-w-64' }"
        :text="t('login.remember_password_tooltip')"
      >
        <template #activator>
          <RuiIcon
            name="lu-circle-question-mark"
            color="primary"
          />
        </template>
      </RuiTooltip>
    </div>
  </div>
</template>
