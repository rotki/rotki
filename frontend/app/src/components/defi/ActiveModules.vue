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
const { dark } = useTheme();

const style = computed(() => ({
  background: get(dark) ? '#1E1E1E' : 'white',
  width: `${get(modules).length * 38}px`
}));

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

const { tc } = useI18n();

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
      title: tc('active_modules.enable.title'),
      message: tc(
        'active_modules.enable.description',
        0,
        getName(get(confirmEnable))
      ),
      type: 'info'
    },
    enableModule
  );
};
</script>

<template>
  <v-row justify="end">
    <v-col cols="auto">
      <v-sheet outlined :style="style">
        <v-row align="center" justify="center" no-gutters>
          <v-col
            v-for="module in moduleStatus"
            :key="module.identifier"
            cols="auto"
          >
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  v-bind="attrs"
                  icon
                  :class="module.enabled ? null : 'active-modules__disabled'"
                  v-on="on"
                  @click="onModulePress(module)"
                >
                  <v-img
                    width="24px"
                    height="24px"
                    contain
                    :src="icon(module.identifier)"
                  />
                </v-btn>
              </template>
              <span v-if="module.enabled">
                {{
                  tc(
                    'active_modules.view_addresses',
                    0,
                    getName(module.identifier)
                  )
                }}
              </span>
              <span v-else>
                {{
                  tc('active_modules.activate', 0, getName(module.identifier))
                }}
              </span>
            </v-tooltip>
          </v-col>
        </v-row>
      </v-sheet>
      <queried-address-dialog
        v-if="manageModule"
        :module="manageModule"
        @close="manageModule = null"
      />
    </v-col>
  </v-row>
</template>

<style scoped lang="scss">
.active-modules {
  &__disabled {
    filter: grayscale(100%);
  }
}
</style>
