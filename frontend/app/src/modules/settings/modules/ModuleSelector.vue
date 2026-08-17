<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import { transformCase, Zero } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import QueriedAddressDialog from '@/modules/accounts/QueriedAddressDialog.vue';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { Module, SUPPORTED_MODULES, type SupportedModule } from '@/modules/core/common/modules';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import AppImage from '@/modules/shell/components/AppImage.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

type ModuleEntry = SupportedModule & { enabled: boolean };

const { t } = useI18n({ useScope: 'global' });

const supportedModules = SUPPORTED_MODULES;
const loading = ref(false);
const search = ref('');
const manageModule = ref<Module>();

const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { fetchQueriedAddresses } = useQueriedAddressOperations();
const activeModules = useSetting('activeModules');
const { update: updateSettings } = useSettingsOperations();

const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
const { submitTask } = useNativeTask();

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

  // Ephemeral, so it never shows up as work: this exists only so what a module feeds can declare a
  // `staleAfter` edge against it. The direction is part of the id, because enabling a module makes
  // its data fetchable while disabling it does not.
  await submitTask({
    ephemeral: true,
    id: makeActivityId(ActivityKind.MODULE_TOGGLE, module, enabled ? 'enabled' : 'disabled'),
    kind: ActivityKind.MODULE_TOGGLE,
    run: async (): Promise<Result<void, TaskError>> => {
      try {
        await update(modules);
        return ok(undefined);
      }
      catch (error: unknown) {
        return err(TaskFailed({ cause: error, message: getErrorMessage(error) }));
      }
    },
    title: t('module_selector.tasks.toggle'),
  });

  if (module === Module.NFTS && !enabled)
    clearNfBalances();
}

/**
 * Applies a bulk module change, announcing each module whose state actually flips as its own
 * `MODULE_TOGGLE` activity.
 *
 * Bulk enable/disable used to call `update` straight through, so it announced nothing: consumers
 * declare their edges per module and direction (`use-nft-balances.ts` keys on
 * `module_toggle:nfts:enabled`), and "Enable all" with NFTs previously off therefore left NFT
 * balances stale indefinitely. One shared settings write, several identities — the work is a
 * single call, but "NFTs became enabled" is what a consumer can subscribe to.
 */
async function applyBulk(next: Module[]): Promise<void> {
  const active = get(activeModules);
  const changed = supportedModules
    .map(module => module.identifier)
    .filter(module => active.includes(module) !== next.includes(module));

  if (changed.length === 0)
    return;

  // Folded to a Result here, not inside `run`: the scheduler calls `run` on a later tick, so a
  // rejection would have no handler attached at the moment it happens.
  const written = update(next).then(
    (): Result<void, TaskError> => ok(undefined),
    (error: unknown): Result<void, TaskError> => err(TaskFailed({ cause: error, message: getErrorMessage(error) })),
  );

  await Promise.all(changed.map(async module => submitTask({
    ephemeral: true,
    id: makeActivityId(ActivityKind.MODULE_TOGGLE, module, next.includes(module) ? 'enabled' : 'disabled'),
    kind: ActivityKind.MODULE_TOGGLE,
    run: async (): Promise<Result<void, TaskError>> => written,
    title: t('module_selector.tasks.toggle'),
  })));
}

async function enableAll() {
  await applyBulk(supportedModules.map(x => x.identifier));
}

async function disableAll() {
  const active = get(activeModules);
  await applyBulk([]);
  if (active.includes(Module.NFTS))
    clearNfBalances();
}

function selected(identifier: Module) {
  const index = transformCase(identifier, true);
  const addresses = get(queriedAddresses)[index];
  if (!addresses || addresses.length === 0)
    return t('module_selector.all_accounts');

  return t('module_selector.some_accounts', {
    number: addresses.length,
  });
}

onMounted(async () => {
  await fetchQueriedAddresses();
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
          data-testid="modules_enable_all"
          @click="enableAll()"
        >
          {{ t('module_selector.actions.enable_all') }}
        </RuiButton>

        <RuiButton
          color="primary"
          variant="outlined"
          :loading="loading"
          class="!py-2"
          data-testid="modules_disable_all"
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
        <div class="flex items-center gap-2">
          <AppImage
            class="icon-bg"
            size="1.5rem"
            fit="contain"
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
          data-testid="module-switch"
          :data-key="row.identifier"
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
