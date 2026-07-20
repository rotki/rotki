<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import { useScrambleSetting } from '@/modules/settings/use-scramble-settings';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  handleMultiplierUpdate,
  randomMultiplier,
  modelScrambleData,
  modelScrambleMultiplier,
} = useScrambleSetting();
</script>

<template>
  <SettingsItem setting-key="scrambleData">
    <template #title>
      {{ t('frontend_settings.scramble.title') }}
    </template>

    <SettingSwitch
      class="my-2"
      setting="scrambleData"
      :label="t('frontend_settings.scramble.label')"
      :error-message="t('frontend_settings.scramble.validation.error')"
    />
    <div class="flex flex-col gap-2">
      <AmountInput
        v-model="modelScrambleMultiplier"
        :label="t('frontend_settings.scramble.multiplier.label')"
        :hint="t('frontend_settings.scramble.multiplier.hint')"
        variant="outlined"
        :disabled="!modelScrambleData"
        @update:model-value="handleMultiplierUpdate($event)"
      >
        <template #append>
          <RuiButton
            variant="text"
            icon
            :disabled="!modelScrambleData"
            @click="handleMultiplierUpdate(randomMultiplier())"
          >
            <RuiIcon name="lu-shuffle" />
          </RuiButton>
        </template>
      </AmountInput>
    </div>
  </SettingsItem>
</template>
