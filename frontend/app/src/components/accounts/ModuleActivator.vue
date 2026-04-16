<script setup lang="ts">
import type { CamelCase } from '@/modules/common/common-types';
import { transformCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import { useAccountLoading } from '@/composables/accounts/loading';
import { type Module, SUPPORTED_MODULES } from '@/modules/common/modules';
import { useQueriedAddressOperations } from '@/modules/session/use-queried-address-operations';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const emit = defineEmits<{
  'update:selection': [modules: Module[]];
}>();

const enabledModules = ref<Module[]>([]);
const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { fetchQueriedAddresses } = useQueriedAddressOperations();

function updateSelection(modules: Module[]) {
  emit('update:selection', modules);
}

function hasAddresses(module: Module) {
  const index = transformCase(module, true) as CamelCase<Module>;
  const addresses = get(queriedAddresses)[index];
  if (addresses)
    return addresses.length > 0;

  return false;
}

const visibleModules = computed(() =>
  SUPPORTED_MODULES.filter((module) => {
    const identifier = module.identifier;
    const isActive = get(activeModules).includes(identifier);
    const activeWithQueried = isActive && hasAddresses(identifier);
    return activeWithQueried || !isActive;
  }),
);

onMounted(async () => await fetchQueriedAddresses());

const { t } = useI18n({ useScope: 'global' });
const { isAccountOperationRunning } = useAccountLoading();
const loading = isAccountOperationRunning();
</script>

<template>
  <div
    v-if="visibleModules.length > 0"
    class="flex flex-col items-start gap-4"
  >
    <div>
      <div class="text-body-1 font-bold text-rui-text">
        {{ t('module_activator.title') }}
      </div>
      <div class="text-body-2 text-rui-text-secondary">
        {{ t('module_activator.subtitle') }}
      </div>
    </div>

    <RuiButtonGroup
      v-model="enabledModules"
      variant="outlined"
      color="primary"
      :disabled="loading"
      @change="updateSelection($event)"
    >
      <RuiButton
        v-for="module in visibleModules"
        :key="module.identifier"
        icon
        type="button"
        :disabled="loading"
        :model-value="module.identifier"
      >
        <RuiTooltip
          class="flex"
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <AppImage
              height="24px"
              width="24px"
              contain
              :src="module.icon"
            />
          </template>
          <span>{{ module.name }}</span>
        </RuiTooltip>
      </RuiButton>
    </RuiButtonGroup>
    <div class="text-caption text-rui-text-secondary">
      {{ t('module_activator.hint') }}
    </div>
  </div>
</template>
