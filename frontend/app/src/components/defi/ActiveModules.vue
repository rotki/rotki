<script setup lang="ts">
import { type PropType, type Ref } from 'vue';
import { type Nullable } from '@/types';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';

interface ModuleWithStatus {
  readonly identifier: Module;
  readonly enabled: boolean;
}

const props = defineProps({
  modules: { required: true, type: Array as PropType<Module[]> }
});
const { modules } = toRefs(props);
const manageModule: Ref<Nullable<Module>> = ref(null);
const confirmEnable: Ref<Nullable<Module>> = ref(null);

const supportedModules = SUPPORTED_MODULES;

const { fetchQueriedAddresses } = useQueriedAddressesStore();
const { update } = useSettingsStore();
const { activeModules } = storeToRefs(useGeneralSettingsStore());

const moduleStatus = computed(() => {
  const active = get(activeModules);
  return get(modules)
    .map(module => ({
      identifier: module,
      enabled: active.includes(module)
    }))
    .sort((a, b) => (a.enabled === b.enabled ? 0 : a.enabled ? -1 : 1));
});

const onModulePress = (module: ModuleWithStatus) => {
  if (module.enabled) {
    set(manageModule, module.identifier);
  } else {
    showConfirmation();
    set(confirmEnable, module.identifier);
  }
};

const enableModule = async () => {
  const module = get(confirmEnable);
  assert(module !== null);
  await update({
    activeModules: [...get(activeModules), module]
  });
  set(confirmEnable, null);
};

const name = (module: string): string => {
  const data = supportedModules.find(value => value.identifier === module);
  return data?.name ?? '';
};

const icon = (module: Module): string => {
  const data = supportedModules.find(value => value.identifier === module);
  return data?.icon ?? '';
};

const { t } = useI18n();

const getName = (module: Nullable<Module>) => ({
  name: module ? name(module) : ''
});

onMounted(async () => {
  await fetchQueriedAddresses();
});

const { show } = useConfirmStore();

const showConfirmation = () => {
  show(
    {
      title: t('active_modules.enable.title'),
      message: t(
        'active_modules.enable.description',
        getName(get(confirmEnable))
      ),
      type: 'info'
    },
    enableModule
  );
};
</script>

<template>
  <div class="flex flex-row items-center justify-end border rounded">
    <div
      v-for="module in moduleStatus"
      :key="module.identifier"
      class="flex flex-column"
    >
      <RuiTooltip open-delay="400" top>
        <template #activator="{ on, attrs }">
          <RuiButton
            v-bind="attrs"
            icon
            variant="text"
            :class="module.enabled ? null : 'active-modules__disabled'"
            v-on="on"
            @click="onModulePress(module)"
          >
            <VImg
              width="24px"
              height="24px"
              contain
              :src="icon(module.identifier)"
            />
          </RuiButton>
        </template>
        <span v-if="module.enabled">
          {{ t('active_modules.view_addresses', getName(module.identifier)) }}
        </span>
        <span v-else>
          {{ t('active_modules.activate', getName(module.identifier)) }}
        </span>
      </RuiTooltip>
    </div>
    <QueriedAddressDialog
      v-if="manageModule"
      :module="manageModule"
      @close="manageModule = null"
    />
  </div>
</template>
