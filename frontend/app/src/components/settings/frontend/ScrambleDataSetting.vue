<script setup lang="ts">
const { scrambleData: enabled, scrambleMultiplier: multiplier } =
  useSessionSettingsStore();

const scrambleData = ref<boolean>(false);
const scrambleMultiplier = ref<string>('0');

onMounted(() => {
  set(scrambleData, get(enabled));
  set(scrambleMultiplier, get(multiplier).toString());
});

const randomMultiplier = () => {
  set(scrambleMultiplier, generateRandomScrambleMultiplier().toString());
};

const { t, tc } = useI18n();
const css = useCssModule();
</script>

<template>
  <div>
    <settings-option
      #default="{ error, success, update }"
      setting="scrambleData"
      session-setting
      :error-message="tc('frontend_settings.validation.scramble.error')"
    >
      <v-switch
        v-model="scrambleData"
        class="general-settings__fields__scramble-data"
        :label="t('frontend_settings.label.scramble')"
        :success-messages="success"
        :error-messages="error"
        @change="update($event)"
      />
    </settings-option>
    <settings-option
      #default="{ error, success, update }"
      class="pt-4"
      setting="scrambleMultiplier"
      session-setting
    >
      <div :class="css.multiplier">
        <amount-input
          v-model="scrambleMultiplier"
          class="general-settings__fields__scramble-multiplier"
          :label="t('frontend_settings.label.scramble_multiplier')"
          :hint="t('frontend_settings.subtitle.scramble_multiplier')"
          outlined
          :disabled="!scrambleData"
          :success-messages="success"
          :error-messages="error"
          @change="update($event)"
        >
          <template #append>
            <v-btn
              icon
              class="mt-n2"
              :disabled="!scrambleData"
              @click="randomMultiplier()"
            >
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </template>
        </amount-input>
      </div>
    </settings-option>
  </div>
</template>

<style module lang="scss">
.multiplier {
  max-width: 520px;
}
</style>
