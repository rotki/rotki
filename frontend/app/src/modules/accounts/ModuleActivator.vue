<script setup lang="ts">
import { transformCase } from '@rotki/common';
import { useAccountLoading } from '@/modules/accounts/use-account-loading';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { type Module, SUPPORTED_MODULES } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useSetting } from '@/modules/settings/use-setting';
import AppImage from '@/modules/shell/components/AppImage.vue';

const emit = defineEmits<{
  'update:selection': [modules: Module[]];
}>();

const enabledModules = ref<Module[]>([]);
const activeModules = useSetting('activeModules');
const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { fetchQueriedAddresses } = useQueriedAddressOperations();

function updateSelection(modules: Module[]) {
  emit('update:selection', modules);
}

function hasAddresses(module: Module) {
  const index = transformCase(module, true);
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
  <!-- laid out like the fields around it: a label, the control, then helper text -->
  <div
    v-if="visibleModules.length > 0"
    class="flex flex-col items-start"
  >
    <div class="mb-1 text-sm leading-5 font-medium text-rui-text">
      {{ t('module_activator.title') }}
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
          :options="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <AppImage
              height="20px"
              width="20px"
              fit="contain"
              :src="module.icon"
            />
          </template>
          <span>{{ module.name }}</span>
        </RuiTooltip>
      </RuiButton>
    </RuiButtonGroup>
    <div class="mt-1.5 text-caption text-rui-text-secondary">
      <p>{{ t('module_activator.subtitle') }}</p>
      <p>{{ t('module_activator.hint') }}</p>
    </div>
  </div>
</template>
