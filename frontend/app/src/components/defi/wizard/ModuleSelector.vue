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
    value: 'name'
  },
  {
    text: t('module_selector.table.enabled'),
    value: 'enabled',
    align: 'end',
    cellClass: 'd-flex justify-end align-center'
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
  <Card flat no-padding :outlined="false">
    <template #search>
      <div class="flex flex-row">
        <div>
          <RuiButton
            color="primary"
            :loading="loading"
            data-cy="modules_enable_all"
            @click="enableAll()"
          >
            {{ t('module_selector.actions.enable_all') }}
          </RuiButton>
          <RuiButton
            color="primary"
            class="ml-2"
            data-cy="modules_disable_all"
            @click="disableAll()"
          >
            {{ t('module_selector.actions.disable_all') }}
          </RuiButton>
        </div>
        <VSpacer />
        <VTextField
          v-model="search"
          :label="t('module_selector.filter')"
          clearable
          outlined
          dense
          prepend-inner-icon="mdi-magnify"
        />
      </div>
    </template>
    <DataTable :headers="headers" :items="modules" :loading="loading">
      <template #item.name="{ item }">
        <div class="flex flex-row items-center">
          <AdaptiveWrapper
            class="flex items-center mr-4"
            width="26px"
            height="26px"
          >
            <VImg width="26px" contain max-height="24px" :src="item.icon" />
          </AdaptiveWrapper>
          <span> {{ item.name }}</span>
        </div>
      </template>
      <template #item.enabled="{ item }">
        <VSwitch
          :data-cy="`${item.identifier}-module-switch`"
          :disabled="loading"
          :input-value="item.enabled"
          hide-details
          class="mt-0 pt-0"
          @change="switchModule(item.identifier, $event)"
        />
      </template>
    </DataTable>
  </Card>
</template>
