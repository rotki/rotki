<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import { Routes } from '@/router/routes';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';

defineProps<{
  modules: Module[];
}>();

function name(module: string): string {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.name ?? '';
}

function icon(module: Module): string {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.icon ?? '';
}

const { t } = useI18n();

const wrapper = ref();
const { top } = useElementBounding(wrapper);
</script>

<template>
  <div
    ref="wrapper"
    :style="`height: calc(100vh - ${top + 100}px);`"
    class="flex flex-col items-center justify-center"
  >
    <div class="module-not-active__container flex flex-col items-center gap-8">
      <div class="flex items-center justify-center gap-4">
        <div
          v-for="module in modules"
          :key="module"
        >
          <AppImage
            width="82px"
            contain
            :src="icon(module)"
          />
        </div>
      </div>
      <i18n-t
        tag="span"
        keypath="module_not_active.not_active"
        class="text-center text-rui-text-secondary"
      >
        <template #link>
          <InternalLink
            class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
            :to="Routes.SETTINGS_MODULES"
          >
            {{ t('module_not_active.settings_link') }}
          </InternalLink>
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
      </i18n-t>
    </div>
  </div>
</template>

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
