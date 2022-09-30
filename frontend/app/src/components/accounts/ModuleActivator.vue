<template>
  <v-row v-if="visibleModules.length > 0">
    <v-col>
      <div class="font-weight-medium">{{ t('module_activator.title') }}</div>
      <div class="text-caption text--secondary">
        {{ t('module_activator.subtitle') }}
      </div>
      <v-btn-toggle
        v-model="enabledModules"
        multiple
        class="mt-2"
        @change="updateSelection($event)"
      >
        <v-btn
          v-for="module in visibleModules"
          :key="module.identifier"
          icon
          :value="module.identifier"
          color="primary"
          depressed
          cols="auto"
        >
          <v-tooltip top open-delay="400">
            <template #activator="{ on, attrs }">
              <v-img
                height="24px"
                width="24px"
                contain
                :src="module.icon"
                v-bind="attrs"
                v-on="on"
              />
            </template>
            <span>{{ module.name }}</span>
          </v-tooltip>
        </v-btn>
      </v-btn-toggle>
      <div class="text-caption text--secondary mt-1 mb-2">
        {{ t('module_activator.hint') }}
      </div>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { Ref } from 'vue';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module, SUPPORTED_MODULES } from '@/types/modules';

const emit = defineEmits(['update:selection']);

const enabledModules: Ref<Module[]> = ref([]);
const { activeModules } = storeToRefs(useGeneralSettingsStore());
let queriedAddressesStore = useQueriedAddressesStore();
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

const visibleModules = computed(() => {
  return SUPPORTED_MODULES.filter(module => {
    const identifier = module.identifier;
    const isActive = get(activeModules).includes(identifier);
    const activeWithQueried = isActive && hasAddresses(identifier);
    return activeWithQueried || !isActive;
  });
});

onMounted(async () => await queriedAddressesStore.fetchQueriedAddresses());

const { t } = useI18n();
</script>
