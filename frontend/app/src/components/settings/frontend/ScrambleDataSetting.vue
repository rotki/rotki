<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useScrambleSetting } from '@/composables/scramble-settings';

const { t } = useI18n({ useScope: 'global' });

const {
  handleMultiplierUpdate,
  randomMultiplier,
  scrambleData,
  scrambleMultiplier,
} = useScrambleSetting();
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('frontend_settings.scramble.title') }}
    </template>

    <SettingsOption
      #default="{ error, success, updateImmediate }"
      setting="scrambleData"
      frontend-setting
      :error-message="t('frontend_settings.scramble.validation.error')"
    >
      <RuiSwitch
        v-model="scrambleData"
        color="primary"
        class="my-2"
        :label="t('frontend_settings.scramble.label')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </SettingsOption>
    <div class="flex flex-col gap-2">
      <AmountInput
        v-model="scrambleMultiplier"
        :label="t('frontend_settings.scramble.multiplier.label')"
        :hint="t('frontend_settings.scramble.multiplier.hint')"
        variant="outlined"
        :disabled="!scrambleData"
        @update:model-value="handleMultiplierUpdate($event)"
      >
        <template #append>
          <RuiButton
            variant="text"
            icon
            :disabled="!scrambleData"
            @click="handleMultiplierUpdate(randomMultiplier())"
          >
            <RuiIcon name="lu-shuffle" />
          </RuiButton>
        </template>
      </AmountInput>
    </div>
  </SettingsItem>
</template>
