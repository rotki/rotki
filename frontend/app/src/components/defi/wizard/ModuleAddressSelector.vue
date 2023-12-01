<script setup lang="ts">
import { SUPPORTED_MODULES } from '@/types/modules';

const { inc: nextStep, dec: previousStep, count: step } = useCounter(1);
const { fetchQueriedAddresses } = useQueriedAddressesStore();
const { activeModules } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const supportedModules = SUPPORTED_MODULES;

const modules = computed(() => {
  const active = get(activeModules);
  if (active.length === 0) {
    return supportedModules;
  }
  return supportedModules.filter(module => active.includes(module.identifier));
});

const steps = computed(() => get(modules).length);

onMounted(async () => {
  await fetchQueriedAddresses();
});
</script>

<template>
  <div>
    <VStepper v-model="step" class="module-address-selector">
      <RuiCard no-padding>
        <VStepperHeader>
          <template v-for="n in steps">
            <VStepperStep
              :key="`${n}-step`"
              :complete="step > n"
              :step="n"
              editable
            >
              <span class="flex flex-col items-center justify-start">
                <AdaptiveWrapper>
                  <VImg
                    width="24px"
                    contain
                    max-height="24px"
                    :src="modules[n - 1].icon"
                  />
                </AdaptiveWrapper>
                <span v-if="modules[n - 1].name" class="mt-3 text-center">
                  {{ modules[n - 1].name }}
                </span>
              </span>
            </VStepperStep>

            <RuiDivider v-if="n !== steps" :key="n" />
          </template>
        </VStepperHeader>
      </RuiCard>

      <VStepperItems>
        <VStepperContent v-for="n in steps" :key="`${n}-content`" :step="n">
          <div class="flex items-center gap-3">
            <AdaptiveWrapper>
              <VImg
                width="30px"
                contain
                max-height="24px"
                :src="modules[n - 1].icon"
              />
            </AdaptiveWrapper>
            <div class="text-h6">{{ modules[n - 1].name }}</div>
          </div>

          <div class="mb-12 mt-4">
            <ModuleQueriedAddress :module="modules[n - 1].identifier" />
          </div>

          <div class="flex gap-4">
            <RuiButton
              v-if="step > 1"
              variant="text"
              color="primary"
              @click="previousStep()"
            >
              {{ t('common.actions.back') }}
            </RuiButton>
            <RuiButton
              v-if="step < modules.length"
              color="primary"
              @click="nextStep()"
            >
              {{ t('common.actions.next') }}
            </RuiButton>
          </div>
        </VStepperContent>
      </VStepperItems>
    </VStepper>
  </div>
</template>

<style scoped lang="scss">
.v-stepper {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;

  &__header {
    border: none !important;
    box-shadow: none !important;
    overflow-x: auto;
    height: 140px;
    flex-wrap: nowrap;

    hr {
      display: none;
    }
  }

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-stepper__step) {
    padding: 24px;

    .v-stepper {
      &__step {
        &__step {
          display: none !important;
        }
      }

      &__label {
        height: 100%;
        min-width: 100px;
        display: block;
      }
    }
  }

  &__items {
    margin-top: 24px;
    border-radius: 4px;
    border: thin solid var(--border-color);
  }

  /* stylelint-enable selector-class-pattern,selector-nested-pattern */
}
</style>
