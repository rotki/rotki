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
                  $t('active_modules.view_addresses', {
                    name: name(module.identifier)
                  })
                }}
              </span>
              <span v-else>
                {{
                  $t('active_modules.activate', {
                    name: name(module.identifier)
                  })
                }}
              </span>
            </v-tooltip>
          </v-col>
        </v-row>
      </v-sheet>
      <queried-address-dialog
        :module="manageModule"
        @close="manageModule = null"
      />
      <confirm-dialog
        :title="$t('active_modules.enable.title')"
        :message="
          $t('active_modules.enable.description', { name: name(confirmEnable) })
        "
        :display="!!confirmEnable"
        @cancel="confirmEnable = null"
        @confirm="enableModule()"
      />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  Ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import QueriedAddressDialog from '@/components/defi/QueriedAddressDialog.vue';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { useTheme } from '@/composables/common';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Nullable } from '@/types';
import { Module } from '@/types/modules';
import { assert } from '@/utils/assertions';

type ModuleWithStatus = {
  readonly identifier: Module;
  readonly enabled: boolean;
};

export default defineComponent({
  name: 'ActiveModules',
  components: { ConfirmDialog, QueriedAddressDialog },
  props: {
    modules: { required: true, type: Array as PropType<Module[]> }
  },
  setup(props) {
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

    onMounted(async () => {
      await fetchQueriedAddresses();
    });

    return {
      manageModule,
      confirmEnable,
      moduleStatus,
      style,
      onModulePress,
      enableModule,
      name,
      icon
    };
  }
});
</script>

<style scoped lang="scss">
.active-modules {
  &__disabled {
    filter: grayscale(100%);
  }
}
</style>
