<script setup lang="ts">
import { type Ref } from 'vue';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';

const emit = defineEmits(['update:selection']);

const enabledModules: Ref<Module[]> = ref([]);
const { activeModules } = storeToRefs(useGeneralSettingsStore());
const queriedAddressesStore = useQueriedAddressesStore();
const { queriedAddresses } = storeToRefs(queriedAddressesStore);

const updateSelection = (modules: string[]) => {
  emit('update:selection', modules);
};

const hasAddresses = (module: Module) => {
  const addresses = get(queriedAddresses)[module];
  if (addresses) {
    return addresses.length > 0;
  }
  return false;
};

const visibleModules = computed(() =>
  SUPPORTED_MODULES.filter(module => {
    const identifier = module.identifier;
    const isActive = get(activeModules).includes(identifier);
    const activeWithQueried = isActive && hasAddresses(identifier);
    return activeWithQueried || !isActive;
  })
);

onMounted(async () => await queriedAddressesStore.fetchQueriedAddresses());

const { t } = useI18n();
const { isAccountOperationRunning } = useAccountLoading();
const loading = isAccountOperationRunning();
</script>

<template>
  <div v-if="visibleModules.length > 0" class="flex flex-col gap-4">
    <div>
      <div class="text-body-1 font-bold text-rui-text">
        {{ t('module_activator.title') }}
      </div>
      <div class="text-body-2 text-rui-text-secondary">
        {{ t('module_activator.subtitle') }}
      </div>
    </div>

    <VBtnToggle
      v-model="enabledModules"
      multiple
      :disabled="loading"
      @change="updateSelection($event)"
    >
      <VBtn
        v-for="module in visibleModules"
        :key="module.identifier"
        icon
        :disabled="loading"
        :value="module.identifier"
        color="primary"
        depressed
        cols="auto"
      >
        <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
          <template #activator>
            <VImg height="24px" width="24px" contain :src="module.icon" />
          </template>
          <span>{{ module.name }}</span>
        </RuiTooltip>
      </VBtn>
    </VBtnToggle>
    <div class="text-caption text--secondary">
      {{ t('module_activator.hint') }}
    </div>
  </div>
</template>
