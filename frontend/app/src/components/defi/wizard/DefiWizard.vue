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
    <VCard>
      <VStepper v-model="step" vertical>
        <VStepperStep :complete="step > 1" step="1">
          {{ t('defi_wizard.steps.setup.title') }}
        </VStepperStep>
        <VStepperContent step="1">
          <Card class="mb-8" outlined>
            <template #title>
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
          </Card>
          <div class="pb-4">
            <VBtn text class="defi-wizard__use-default" @click="done()">
              {{ t('defi_wizard.steps.setup.used_default') }}
            </VBtn>
            <VBtn
              color="primary"
              class="defi-wizard__select-modules ml-4"
              @click="step = 2"
            >
              {{ t('common.actions.continue') }}
            </VBtn>
          </div>
        </VStepperContent>
        <VStepperStep :complete="step > 2" step="2">
          {{ t('defi_wizard.steps.select_modules.title') }}
        </VStepperStep>
        <VStepperContent step="2">
          <Card outlined class="mb-8">
            <template #title>
              {{ t('defi_wizard.steps.select_modules.subtitle') }}
            </template>
            <template #subtitle>
              {{ t('defi_wizard.steps.select_modules.hint') }}
            </template>
            <ModuleSelector />
          </Card>
          <div class="pb-4">
            <VBtn text @click="step = 1">
              {{ t('common.actions.back') }}
            </VBtn>
            <VBtn
              color="primary"
              class="defi-wizard__select-accounts ml-4"
              @click="step = 3"
            >
              {{ t('common.actions.continue') }}
            </VBtn>
          </div>
        </VStepperContent>
        <VStepperStep :complete="step > 3" step="3">
          {{ t('defi_wizard.steps.select_accounts.title') }}
        </VStepperStep>
        <VStepperContent step="3">
          <Card outlined class="mb-8">
            <template #title>
              {{ t('defi_wizard.steps.select_accounts.subtitle') }}
            </template>
            <template #subtitle>
              {{ t('defi_wizard.steps.select_accounts.hint') }}
            </template>
            <ModuleAddressSelector class="defi-wizard__address-selector" />
          </Card>
          <div class="pb-4">
            <VBtn text @click="step = 2">
              {{ t('common.actions.back') }}
            </VBtn>
            <VBtn
              color="primary"
              class="defi-wizard__done ml-4"
              @click="done()"
            >
              {{ t('common.actions.continue') }}
            </VBtn>
          </div>
        </VStepperContent>
      </VStepper>
    </VCard>
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
