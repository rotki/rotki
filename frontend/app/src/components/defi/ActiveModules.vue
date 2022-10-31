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
                  x-small
                  v-bind="attrs"
                  icon
                  class="ma-2"
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
      <confirm-dialog
        :title="tc('active_modules.enable.title')"
        :message="
          tc('active_modules.enable.description', 0, getName(confirmEnable))
        "
        :display="!!confirmEnable"
        @cancel="confirmEnable = null"
        @confirm="enableModule()"
      />
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { PropType, Ref } from 'vue';
import QueriedAddressDialog from '@/components/defi/QueriedAddressDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { useTheme } from '@/composables/common';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Nullable } from '@/types';
import { Module, SUPPORTED_MODULES } from '@/types/modules';
import { assert } from '@/utils/assertions';

type ModuleWithStatus = {
  readonly identifier: Module;
  readonly enabled: boolean;
};

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
</script>

<style scoped lang="scss">
.active-modules {
  &__disabled {
    filter: grayscale(100%);
  }
}
</style>
