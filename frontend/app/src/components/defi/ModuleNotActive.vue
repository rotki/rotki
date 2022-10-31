<template>
  <div
    :style="`height: calc(100vh - ${top + 64}px);`"
    class="d-flex flex-column align-center justify-center"
  >
    <div class="module-not-active__container">
      <v-row align="center" justify="center">
        <v-col v-for="module in modules" :key="module" cols="auto">
          <v-img width="82px" contain :src="icon(module)" />
        </v-col>
      </v-row>
      <v-row align="center" justify="center" class="mt-16">
        <v-col cols="auto" class="text--secondary">
          <i18n
            tag="span"
            path="module_not_active.not_active"
            class="text-center"
          >
            <template #link>
              <router-link
                class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
                text
                to="/settings/modules"
                small
              >
                {{ t('module_not_active.settings_link') }}
              </router-link>
            </template>
            <template #text>
              <div v-if="modules.length > 1">
                {{ t('module_not_active.at_least_one') }}
              </div>
            </template>
            <template #module>
              <span
                v-for="module in modules"
                :key="`mod-${module}`"
                class="module-not-active__module"
              >
                {{ name(module) }}
              </span>
            </template>
          </i18n>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getCurrentInstance, onMounted, PropType, ref } from 'vue';

import { Module, SUPPORTED_MODULES } from '@/types/modules';
import { assert } from '@/utils/assertions';

defineProps({
  modules: {
    required: true,
    type: Array as PropType<Module[]>,
    validator: (value: Module[]) =>
      value.every(module => Object.values(Module).includes(module))
  }
});

const top = ref(0);

const name = (module: string): string => {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.name ?? '';
};

const icon = (module: Module): string => {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.icon ?? '';
};

onMounted(() => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance);
  const $el = currentInstance.proxy.$el;
  const { top: topPoint } = $el.getBoundingClientRect();
  set(top, topPoint);
});

const { t } = useI18n();
</script>

<style scoped lang="scss">
.module-not-active {
  &__link {
    text-transform: none !important;
  }

  &__container {
    width: 100%;
  }

  &__module {
    &:not(:first-child) {
      &:before {
        content: '& ';
      }
    }
  }
}
</style>
