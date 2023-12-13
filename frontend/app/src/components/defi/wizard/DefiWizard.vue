<script setup lang="ts">
const { t } = useI18n();

const step = ref<number>(1);

const { updateSetting } = useFrontendSettingsStore();
const done = async () => {
  await updateSetting({ defiSetupDone: true });
};

const steps = computed(() => [
  {
    title: t('defi_wizard.steps.setup.title')
  },
  {
    title: t('defi_wizard.steps.select_modules.title')
  }
]);
</script>

<template>
  <div class="container">
    <RuiCard class="overflow-hidden">
      <div class="flex gap-4">
        <div>
          <RuiStepper
            custom
            :step="step"
            orientation="vertical"
            :steps="steps"
          />
        </div>
        <Transition
          appear
          enter-class="translate-x-5 opacity-0"
          enter-to-class="translate-yx-0 opacity-1"
          enter-active-class="transform duration-300"
          leave-class="-translate-x-0 opacity-1"
          leave-to-class="-translate-x-5 opacity-0"
          leave-active-class="transform duration-100"
          class="my-4 w-full"
        >
          <RuiCard v-if="step === 1">
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
            <template #footer>
              <div class="flex gap-2 p-2">
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
            </template>
          </RuiCard>

          <RuiCard v-else-if="step === 2">
            <template #header>
              {{ t('defi_wizard.steps.select_modules.subtitle') }}
            </template>
            <template #subheader>
              {{ t('defi_wizard.steps.select_modules.hint') }}
            </template>
            <ModuleSelector />
            <template #footer>
              <div class="flex gap-2 p-2">
                <RuiButton color="primary" variant="text" @click="step = 1">
                  {{ t('common.actions.back') }}
                </RuiButton>
                <RuiButton
                  color="primary"
                  data-cy="defi-wizard-done"
                  @click="done()"
                >
                  {{ t('common.actions.continue') }}
                </RuiButton>
              </div>
            </template>
          </RuiCard>
        </Transition>
      </div>
    </RuiCard>
  </div>
</template>
