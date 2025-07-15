<script setup lang="ts">
import type { CamelCase } from '@/types/common';
import { transformCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import { useAccountLoading } from '@/composables/accounts/loading';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';

const emit = defineEmits(['update:selection']);

const enabledModules = ref<Module[]>([]);
const { activeModules } = storeToRefs(useGeneralSettingsStore());
const queriedAddressesStore = useQueriedAddressesStore();
const { queriedAddresses } = storeToRefs(queriedAddressesStore);

function updateSelection(modules: string[]) {
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

onMounted(async () => await queriedAddressesStore.fetchQueriedAddresses());

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
