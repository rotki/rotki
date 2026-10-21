<script setup lang="ts">
import { transformCase, Zero } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import QueriedAddressDialog from '@/modules/accounts/QueriedAddressDialog.vue';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { Module, SUPPORTED_MODULES, type SupportedModule } from '@/modules/core/common/modules';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import ModuleAddressesCell from '@/modules/settings/modules/ModuleAddressesCell.vue';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import IconMark from '@/modules/shell/components/IconMark.vue';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

type ModuleEntry = SupportedModule & { enabled: boolean };

const { t } = useI18n({ useScope: 'global' });

const supportedModules = SUPPORTED_MODULES;
const loading = ref<boolean>(false);
const search = ref<string>('');
const manageModule = ref<Module>();

const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { fetchQueriedAddresses } = useQueriedAddressOperations();
const activeModules = useSetting('activeModules');
const { update: updateSettings } = useSettingsOperations();

const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
const { submitTask } = useNativeTask();

const modules = computed<ModuleEntry[]>(() => {
  const active = get(activeModules);
  const filter = get(search).toLowerCase();
  const filteredModules = filter
    ? supportedModules.filter(m => m.name.toLowerCase().includes(filter))
    : supportedModules;
  return [...filteredModules]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(module => ({
      ...module,
      enabled: active.includes(module.identifier),
    }));
});

/** Each bulk action is offered only while it would change something. */
const allEnabled = computed<boolean>(() => supportedModules.every(m => get(activeModules).includes(m.identifier)));
const noneEnabled = computed<boolean>(() => get(activeModules).length === 0);

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
 * @remarks
 * One settings write, several identities. Consumers subscribe per module and direction
 * (`use-nft-balances.ts` keys on `module-toggle:nfts:enabled`), so a bulk change that announced
 * only itself would leave them stale: "Enable all" would never tell NFT balances they can load.
 */
async function applyBulk(next: Module[]): Promise<void> {
  const active = get(activeModules);
  const changed = supportedModules
    .map(module => module.identifier)
    .filter(module => active.includes(module) !== next.includes(module));

  if (changed.length === 0)
    return;

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

/** No queried addresses means the backend queries every tracked Ethereum address for the module. */
function selected(identifier: Module): string {
  const index = transformCase(identifier, true);
  const addresses = get(queriedAddresses)[index];
  if (!addresses || addresses.length === 0)
    return t('module_selector.all_accounts');

  return t('module_selector.some_accounts', { number: addresses.length }, addresses.length);
}

onMounted(async () => {
  await fetchQueriedAddresses();
});
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <RuiTextField
        v-model="search"
        color="primary"
        class="w-full sm:w-72"
        :placeholder="t('module_selector.filter')"
        clearable
        details="hidden"
        dense
        prepend-icon="lu-search"
      />
      <div class="flex items-center gap-2 ml-auto">
        <RuiButton
          color="primary"
          variant="outlined"
          size="sm"
          :disabled="loading || allEnabled"
          data-testid="modules_enable_all"
          @click="enableAll()"
        >
          {{ t('module_selector.actions.enable_all') }}
        </RuiButton>
        <RuiButton
          color="primary"
          variant="outlined"
          size="sm"
          :disabled="loading || noneEnabled"
          data-testid="modules_disable_all"
          @click="disableAll()"
        >
          {{ t('module_selector.actions.disable_all') }}
        </RuiButton>
      </div>
    </template>

    <RuiTable
      :loading="loading"
      :empty="modules.length === 0 ? { label: t('module_selector.no_match') } : false"
    >
      <thead>
        <tr>
          <th class="w-full">
            {{ t('common.name') }}
          </th>
          <th class="whitespace-nowrap">
            {{ t('module_selector.table.select_accounts') }}
          </th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in modules"
          :key="row.identifier"
        >
          <td>
            <div class="flex items-center gap-3">
              <IconMark
                size="1.25rem"
                :src="row.icon"
              />
              <span class="font-medium">{{ row.name }}</span>
            </div>
          </td>
          <td class="whitespace-nowrap">
            <ModuleAddressesCell
              :enabled="row.enabled"
              :identifier="row.identifier"
              :label="selected(row.identifier)"
              @manage="manageModule = row.identifier"
            />
          </td>
          <td class="w-px">
            <RuiSwitch
              color="primary"
              data-testid="module-switch"
              :data-key="row.identifier"
              :disabled="loading"
              :model-value="row.enabled"
              details="hidden"
              class="mr-2"
              @update:model-value="switchModule(row.identifier, $event)"
            />
          </td>
        </tr>
      </tbody>
    </RuiTable>

    <QueriedAddressDialog
      v-if="manageModule"
      :module="manageModule"
      @close="manageModule = undefined"
    />
  </TableFrame>
</template>
