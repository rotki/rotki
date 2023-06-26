<script setup lang="ts">
import {
  Module,
  SUPPORTED_MODULES,
  type SupportedModule
} from '@/types/modules';
import { Section } from '@/types/status';
import { type DataTableHeader } from '@/types/vuetify';

const { t } = useI18n();

const supportedModules = SUPPORTED_MODULES;
const loading = ref(false);
const search = ref('');

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { update: updateSettings } = useSettingsStore();

const balancesStore = useNonFungibleBalancesStore();
const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('common.name'),
    value: 'name',
    width: '100%'
  },
  {
    text: t('module_selector.table.enabled'),
    value: 'enabled'
  }
]);

const modules = computed<(SupportedModule & { enabled: boolean })[]>(() => {
  const active = get(activeModules);
  const filter = get(search).toLowerCase();
  const filteredModules = filter
    ? supportedModules.filter(m => m.name.toLowerCase().includes(filter))
    : supportedModules;
  return filteredModules.map(module => ({
    ...module,
    enabled: active.includes(module.identifier)
  }));
});

const { start: fetch } = useTimeoutFn(() => resetStatus(), 800, {
  immediate: false
});
const { start: clearNfBalances } = useTimeoutFn(
  () => balancesStore.$reset(),
  800,
  { immediate: false }
);

const update = async (activeModules: Module[]) => {
  set(loading, true);
  await updateSettings({ activeModules });
  set(loading, false);
};

const switchModule = async (module: Module, enabled: boolean) => {
  const active = get(activeModules);
  let modules: Module[];
  if (enabled) {
    modules = [...active, module];
  } else {
    modules = active.filter(m => m !== module);
  }

  await update(modules);
  if (module === Module.NFTS) {
    if (enabled) {
      fetch();
    } else {
      clearNfBalances();
    }
  }
};

const enableAll = async () => {
  const allModules = supportedModules.map(x => x.identifier);
  const active = get(activeModules);
  const activatedModules = allModules.filter(m => !active.includes(m));
  await update(allModules);

  if (activatedModules.includes(Module.NFTS)) {
    fetch();
  }
};

const disableAll = async () => {
  const active = get(activeModules);
  await update([]);
  if (active.includes(Module.NFTS)) {
    clearNfBalances();
  }
};
</script>

<template>
  <card outlined-body flat no-padding>
    <template #search>
      <div class="d-flex flex-row">
        <div>
          <v-btn
            color="primary"
            :loading="loading"
            depressed
            data-cy="modules_enable_all"
            @click="enableAll()"
          >
            {{ t('module_selector.actions.enable_all') }}
          </v-btn>
          <v-btn
            color="primary"
            depressed
            outlined
            text
            class="ml-2"
            data-cy="modules_disable_all"
            @click="disableAll()"
          >
            {{ t('module_selector.actions.disable_all') }}
          </v-btn>
        </div>
        <v-spacer />
        <v-text-field
          v-model="search"
          :label="t('module_selector.filter')"
          clearable
          outlined
          dense
          prepend-inner-icon="mdi-magnify"
        />
      </div>
    </template>
    <data-table :headers="headers" :items="modules" :loading="loading">
      <template #item.name="{ item }">
        <div class="d-flex flex-row align-center">
          <v-avatar left class="d-flex">
            <adaptive-wrapper
              class="d-flex align-center"
              width="26px"
              height="26px"
            >
              <v-img width="26px" contain max-height="24px" :src="item.icon" />
            </adaptive-wrapper>
          </v-avatar>
          <span> {{ item.name }}</span>
        </div>
      </template>
      <template #item.enabled="{ item }">
        <v-switch
          :data-cy="`${item.identifier}-module-switch`"
          :disabled="loading"
          :input-value="item.enabled"
          @change="switchModule(item.identifier, $event)"
        />
      </template>
    </data-table>
  </card>
</template>
