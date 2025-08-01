<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { generateRandomScrambleMultiplier } from '@/utils/session';

const { scrambleData: enabled, scrambleMultiplier: multiplier } = storeToRefs(useFrontendSettingsStore());

const scrambleData = ref<boolean>(false);
const scrambleMultiplier = ref<string>('0');

const { t } = useI18n({ useScope: 'global' });

function randomMultiplier(): string {
  const value = generateRandomScrambleMultiplier().toString();
  set(scrambleMultiplier, value);
  return value;
}

function setData() {
  set(scrambleData, get(enabled));
  set(scrambleMultiplier, (get(multiplier) ?? generateRandomScrambleMultiplier()).toString());
}

onMounted(setData);

watch([enabled, multiplier], setData);
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
    <SettingsOption
      #default="{ error, success, update }"
      setting="scrambleMultiplier"
      frontend-setting
      :error-message="t('frontend_settings.scramble.validation.error')"
    >
      <AmountInput
        v-model="scrambleMultiplier"
        :label="t('frontend_settings.scramble.multiplier.label')"
        :hint="t('frontend_settings.scramble.multiplier.hint')"
        variant="outlined"
        :disabled="!scrambleData"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="update(Number($event))"
      >
        <template #append>
          <RuiButton
            variant="text"
            icon
            :disabled="!scrambleData"
            @click="update(Number(randomMultiplier()))"
          >
            <RuiIcon name="lu-shuffle" />
          </RuiButton>
        </template>
      </AmountInput>
    </SettingsOption>
  </SettingsItem>
</template>
