<script setup lang="ts">
import { ref } from 'vue';

const { updateSetting } = useFrontendSettingsStore();

const step = ref<number>(1);
const done = async () => {
  await updateSetting({ defiSetupDone: true });
};

const { t } = useI18n();
</script>

<template>
  <VContainer>
    <RuiCard no-padding class="overflow-hidden">
      <VStepper v-model="step" vertical>
        <VStepperStep :complete="step > 1" step="1">
          {{ t('defi_wizard.steps.setup.title') }}
        </VStepperStep>
        <VStepperContent step="1">
          <RuiCard class="mb-4">
            <template #header>
              {{ t('defi_wizard.steps.setup.subtitle') }}
            </template>
            <p>
              {{ t('defi_wizard.steps.setup.description_line_one') }}
            </p>
            <p>
              {{ t('defi_wizard.steps.setup.description_line_two') }}
            </p>
            <p>
              {{ t('defi_wizard.steps.setup.description_line_three') }}
            </p>
          </RuiCard>
          <div class="flex gap-2 mb-2">
            <RuiButton
              color="primary"
              variant="text"
              class="defi-wizard__use-default"
              @click="done()"
            >
              {{ t('defi_wizard.steps.setup.used_default') }}
            </RuiButton>
            <RuiButton
              color="primary"
              class="defi-wizard__select-modules"
              @click="step = 2"
            >
              {{ t('common.actions.continue') }}
            </RuiButton>
          </div>
        </VStepperContent>
        <VStepperStep :complete="step > 2" step="2">
          {{ t('defi_wizard.steps.select_modules.title') }}
        </VStepperStep>
        <VStepperContent step="2">
          <RuiCard class="mb-4">
            <template #header>
              {{ t('defi_wizard.steps.select_modules.subtitle') }}
            </template>
            <template #subheader>
              {{ t('defi_wizard.steps.select_modules.hint') }}
            </template>
            <ModuleSelector />
          </RuiCard>
          <div class="flex gap-2 mb-2">
            <RuiButton color="primary" variant="text" @click="step = 1">
              {{ t('common.actions.back') }}
            </RuiButton>
            <RuiButton
              color="primary"
              class="defi-wizard__select-accounts"
              @click="step = 3"
            >
              {{ t('common.actions.continue') }}
            </RuiButton>
          </div>
        </VStepperContent>
        <VStepperStep :complete="step > 3" step="3">
          {{ t('defi_wizard.steps.select_accounts.title') }}
        </VStepperStep>
        <VStepperContent step="3">
          <RuiCard class="mb-4">
            <template #header>
              {{ t('defi_wizard.steps.select_accounts.subtitle') }}
            </template>
            <template #subheader>
              {{ t('defi_wizard.steps.select_accounts.hint') }}
            </template>
            <ModuleAddressSelector class="defi-wizard__address-selector" />
          </RuiCard>
          <div class="flex gap-2 mb-2">
            <RuiButton variant="text" color="primary" @click="step = 2">
              {{ t('common.actions.back') }}
            </RuiButton>
            <RuiButton
              color="primary"
              class="defi-wizard__done"
              @click="done()"
            >
              {{ t('common.actions.continue') }}
            </RuiButton>
          </div>
        </VStepperContent>
      </VStepper>
    </RuiCard>
  </VContainer>
</template>

<style scoped lang="scss">
.defi-wizard {
  &__address-selector {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-stepper__content) {
      margin: auto !important;
      border-left: none !important;
    }

    /* stylelint-enable selector-class-pattern,selector-nested-pattern */
  }
}
</style>
