<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { CamelCase } from '@/types/common';
import { transformCase, Zero } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import QueriedAddressDialog from '@/components/defi/QueriedAddressDialog.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { useStatusUpdater } from '@/composables/status';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module, SUPPORTED_MODULES, type SupportedModule } from '@/types/modules';
import { Section } from '@/types/status';

type ModuleEntry = SupportedModule & { enabled: boolean };

const { t } = useI18n({ useScope: 'global' });

const supportedModules = SUPPORTED_MODULES;
const loading = ref(false);
const search = ref('');
const manageModule = ref<Module>();

const queriedAddressStore = useQueriedAddressesStore();
const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { queriedAddresses } = storeToRefs(queriedAddressStore);
const { update: updateSettings } = useSettingsStore();

const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

const sort = ref<DataTableSortColumn<ModuleEntry>>({
  column: 'name',
  direction: 'asc',
});

const headers = computed<DataTableColumn<ModuleEntry>[]>(() => [{
  class: 'w-full',
  key: 'name',
  label: t('common.name'),
  sortable: true,
}, {
  key: 'selectedAccounts',
  label: t('module_selector.table.select_accounts'),
}, {
  align: 'end',
  cellClass: 'flex justify-end align-center',
  key: 'enabled',
  label: t('module_selector.table.enabled'),
}, {
  align: 'center',
  key: 'actions',
  label: '',
}]);

useRememberTableSorting<ModuleEntry>(TableId.MODULES, sort, headers);

const modules = computed<ModuleEntry[]>(() => {
  const active = get(activeModules);
  const filter = get(search).toLowerCase();
  const filteredModules = filter
    ? supportedModules.filter(m => m.name.toLowerCase().includes(filter))
    : supportedModules;
  return filteredModules.map(module => ({
    ...module,
    enabled: active.includes(module.identifier),
  }));
});

const { start: fetch } = useTimeoutFn(() => resetStatus(), 800, {
  immediate: false,
});
const { start: clearNfBalances } = useTimeoutFn(() => {
  set(nonFungibleTotalValue, Zero);
}, 800, { immediate: false });

async function update(activeModules: Module[]) {
  set(loading, true);
  await updateSettings({ activeModules });
  set(loading, false);
}

async function switchModule(module: Module, enabled: boolean) {
  const active = get(activeModules);
  let modules: Module[];
  if (enabled)
    modules = [...active, module];
  else modules = active.filter(m => m !== module);

  await update(modules);
  if (module === Module.NFTS) {
    if (enabled)
      fetch();
    else clearNfBalances();
  }
}

async function enableAll() {
  const allModules = supportedModules.map(x => x.identifier);
  const active = get(activeModules);
  const activatedModules = allModules.filter(m => !active.includes(m));
  await update(allModules);

  if (activatedModules.includes(Module.NFTS))
    fetch();
}

async function disableAll() {
  const active = get(activeModules);
  await update([]);
  if (active.includes(Module.NFTS))
    clearNfBalances();
}

function selected(identifier: Module) {
  const index = transformCase(identifier, true) as CamelCase<Module>;
  const addresses = get(queriedAddresses)[index];
  if (!addresses || addresses.length === 0)
    return t('module_selector.all_accounts');

  return t('module_selector.some_accounts', {
    number: addresses.length,
  });
}

onMounted(async () => {
  await queriedAddressStore.fetchQueriedAddresses();
});
</script>

<template>
  <RuiCard>
    <div class="flex flex-col md:flex-row md:justify-between gap-4 mb-4">
      <RuiTextField
        v-model="search"
        variant="outlined"
        color="primary"
        class="min-w-[20rem] flex-1"
        :label="t('module_selector.filter')"
        clearable
        hide-details
        dense
        prepend-icon="lu-search"
      />
      <div class="flex items-center gap-2">
        <RuiButton
          color="primary"
          :loading="loading"
          class="!py-2"
          data-cy="modules_enable_all"
          @click="enableAll()"
        >
          {{ t('module_selector.actions.enable_all') }}
        </RuiButton>

        <RuiButton
          color="primary"
          variant="outlined"
          :loading="loading"
          class="!py-2"
          data-cy="modules_disable_all"
          @click="disableAll()"
        >
          {{ t('module_selector.actions.disable_all') }}
        </RuiButton>
      </div>
    </div>

    <RuiDataTable
      v-model:sort="sort"
      :cols="headers"
      :rows="modules"
      row-attr="identifier"
      :loading="loading"
      outlined
      dense
    >
      <template #item.name="{ row }">
        <div class="flex flex-row items-center gap-2">
          <AppImage
            class="icon-bg"
            size="1.5rem"
            contain
            :src="row.icon"
          />
          <span>{{ row.name }}</span>
        </div>
      </template>

      <template #item.selectedAccounts="{ row }">
        <RuiChip
          color="primary"
          placement="center"
          size="sm"
          variant="outlined"
          class="!h-5 !bg-rui-primary-lighter/[0.1] font-medium"
        >
          {{ selected(row.identifier) }}
        </RuiChip>
      </template>

      <template #item.enabled="{ row }">
        <RuiSwitch
          color="primary"
          :data-cy="`${row.identifier}-module-switch`"
          :disabled="loading"
          :model-value="row.enabled"
          hide-details
          class="py-2"
          @update:model-value="switchModule(row.identifier, $event)"
        />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          no-delete
          class="px-4"
          :edit-disabled="!row.enabled"
          :edit-tooltip="t('module_selector.select_accounts_hint')"
          @edit-click="manageModule = row.identifier"
        />
      </template>
    </RuiDataTable>

    <QueriedAddressDialog
      v-if="manageModule"
      :module="manageModule"
      @close="manageModule = undefined"
    />
  </RuiCard>
</template>
