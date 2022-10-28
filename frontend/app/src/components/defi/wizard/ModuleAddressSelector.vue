<template>
  <v-stepper v-model="step" class="module-address-selector">
    <v-sheet rounded outlined>
      <v-stepper-header>
        <template v-for="n in steps">
          <v-stepper-step
            :key="`${n}-step`"
            :complete="step > n"
            :step="n"
            editable
          >
            <span class="d-flex flex-column align-center justify-start">
              <adaptive-wrapper>
                <v-img
                  width="24px"
                  contain
                  max-height="24px"
                  :src="modules[n - 1].icon"
                />
              </adaptive-wrapper>
              <span v-if="modules[n - 1].name" class="mt-3 text-center">
                {{ modules[n - 1].name }}
              </span>
            </span>
          </v-stepper-step>

          <v-divider v-if="n !== steps" :key="n" />
        </template>
      </v-stepper-header>
    </v-sheet>

    <v-stepper-items>
      <v-stepper-content v-for="n in steps" :key="`${n}-content`" :step="n">
        <v-row align="center">
          <v-col cols="auto">
            <adaptive-wrapper>
              <v-img
                width="30px"
                contain
                max-height="24px"
                :src="modules[n - 1].icon"
              />
            </adaptive-wrapper>
          </v-col>
          <v-col>
            <div class="text-h6">{{ modules[n - 1].name }}</div>
          </v-col>
        </v-row>

        <v-card class="mb-12 mt-4" flat height="110px">
          <module-queried-address :module="modules[n - 1].identifier" />
        </v-card>

        <div>
          <v-btn v-if="step > 1" class="mr-4" text @click="previousStep()">
            {{ t('common.actions.back') }}
          </v-btn>
          <v-btn
            v-if="step < modules.length"
            color="primary"
            @click="nextStep()"
          >
            {{ t('common.actions.next') }}
          </v-btn>
        </div>
      </v-stepper-content>
    </v-stepper-items>
  </v-stepper>
</template>

<script setup lang="ts">
import ModuleQueriedAddress from '@/components/defi/wizard/ModuleQueriedAddress.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { SUPPORTED_MODULES } from '@/types/modules';

const { inc: nextStep, dec: previousStep, count: step } = useCounter(-1);
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

<!--suppress Stylelint -->
<style scoped lang="scss">
.module-address-selector {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;

  :deep() {
    .v-stepper {
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

      &__step {
        padding: 24px;

        &__step {
          display: none !important;
        }
      }

      &__label {
        height: 100%;
        min-width: 100px;
        display: block;
      }

      &__items {
        margin-top: 24px;
        border-radius: 4px;
        border: thin solid rgba(0, 0, 0, 0.12);
      }

      /* stylelint-disable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
      .theme--dark &__items {
        border: thin solid rgba(255, 255, 255, 0.12);
      }
      /* stylelint-enable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
    }
  }
}
</style>
