<script setup lang="ts">
import { type DataTableColumn } from '@rotki/ui-library-compat';
import {
  Module,
  SUPPORTED_MODULES,
  type SupportedModule
} from '@/types/modules';
import { Section } from '@/types/status';
import { type CamelCase } from '@/types/common';

const { t } = useI18n();

const supportedModules = SUPPORTED_MODULES;
const loading = ref(false);
const search = ref('');
const manageModule = ref<Module>();

const queriedAddressStore = useQueriedAddressesStore();
const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { queriedAddresses } = storeToRefs(queriedAddressStore);
const { update: updateSettings } = useSettingsStore();

const balancesStore = useNonFungibleBalancesStore();
const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('common.name'),
    key: 'name',
    class: 'w-full'
  },
  {
    label: t('module_selector.table.select_accounts'),
    key: 'selectedAccounts'
  },
  {
    label: t('module_selector.table.enabled'),
    key: 'enabled',
    align: 'end',
    cellClass: 'flex justify-end align-center'
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

const selected = (identifier: Module) => {
  const index = transformCase(identifier, true) as CamelCase<Module>;
  const addresses = get(queriedAddresses)[index];
  if (!addresses || addresses.length === 0) {
    return t('module_selector.all_accounts');
  }
  return addresses.length.toString();
};

onMounted(async () => {
  await queriedAddressStore.fetchQueriedAddresses();
});
</script>

<template>
  <div>
    <div class="flex flex-col md:flex-row md:justify-between gap-4 mb-4">
      <div class="flex items-center gap-2">
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
          variant="outlined"
          data-cy="modules_disable_all"
          @click="disableAll()"
        >
          {{ t('module_selector.actions.disable_all') }}
        </RuiButton>
      </div>

      <RuiTextField
        v-model="search"
        variant="outlined"
        color="primary"
        class="md:min-w-[20rem]"
        :label="t('module_selector.filter')"
        clearable
        hide-details
        dense
        prepend-icon="search-line"
      />
    </div>

    <RuiDataTable
      :cols="headers"
      :rows="modules"
      row-attr="identifier"
      :loading="loading"
      outlined
    >
      <template #item.name="{ row }">
        <div class="flex flex-row items-center">
          <AdaptiveWrapper
            class="flex items-center mr-4"
            width="26px"
            height="26px"
          >
            <AppImage width="26px" contain max-height="24px" :src="row.icon" />
          </AdaptiveWrapper>
          <span> {{ row.name }}</span>
        </div>
      </template>

      <template #item.selectedAccounts="{ row }">
        <div class="flex align-center text-no-wrap">
          <RowActions
            no-delete
            class="px-4"
            :edit-disabled="!row.enabled"
            :edit-tooltip="t('module_selector.select_accounts_hint')"
            @edit-click="manageModule = row.identifier"
          />

          <RuiBadge
            color="primary"
            :text="selected(row.identifier)"
            placement="center"
          />
        </div>
      </template>

      <template #item.enabled="{ row }">
        <VSwitch
          :data-cy="`${row.identifier}-module-switch`"
          :disabled="loading"
          :input-value="row.enabled"
          hide-details
          class="mt-2 pt-0"
          @change="switchModule(row.identifier, $event)"
        />
      </template>
    </RuiDataTable>

    <QueriedAddressDialog
      v-if="manageModule"
      :module="manageModule"
      @close="manageModule = undefined"
    />
  </div>
</template>
