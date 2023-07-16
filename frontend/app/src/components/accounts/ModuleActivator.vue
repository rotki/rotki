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
  <VRow v-if="visibleModules.length > 0">
    <VCol>
      <div class="font-weight-medium">{{ t('module_activator.title') }}</div>
      <div class="text-caption text--secondary">
        {{ t('module_activator.subtitle') }}
      </div>
      <VBtnToggle
        v-model="enabledModules"
        multiple
        :disabled="loading"
        class="mt-2"
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
          <VTooltip top open-delay="400">
            <template #activator="{ on, attrs }">
              <VImg
                height="24px"
                width="24px"
                contain
                :src="module.icon"
                v-bind="attrs"
                v-on="on"
              />
            </template>
            <span>{{ module.name }}</span>
          </VTooltip>
        </VBtn>
      </VBtnToggle>
      <div class="text-caption text--secondary mt-1 mb-2">
        {{ t('module_activator.hint') }}
      </div>
    </VCol>
  </VRow>
</template>
