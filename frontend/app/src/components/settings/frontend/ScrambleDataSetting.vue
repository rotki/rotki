<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSessionSettingsStore } from '@/store/settings/session';
import { generateRandomScrambleMultiplier } from '@/utils/session';

const { scrambleData: enabled, scrambleMultiplier: multiplier } = storeToRefs(useSessionSettingsStore());

const scrambleData = ref<boolean>(false);
const scrambleMultiplier = ref<string>('0');

const { t } = useI18n();

function randomMultiplier() {
  set(scrambleMultiplier, generateRandomScrambleMultiplier().toString());
}

function setData() {
  set(scrambleData, get(enabled));
  set(scrambleMultiplier, get(multiplier).toString());
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
      session-setting
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
      session-setting
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
        @update:model-value="update($event)"
      >
        <template #append>
          <RuiButton
            variant="text"
            icon
            :disabled="!scrambleData"
            @click="randomMultiplier()"
          >
            <RuiIcon name="lu-shuffle" />
          </RuiButton>
        </template>
      </AmountInput>
    </SettingsOption>
  </SettingsItem>
</template>
