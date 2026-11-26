<script setup lang="ts">
import { transformCase } from '@rotki/common';
import { RuiButton, RuiSwitch, RuiTable, RuiTextField } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import QueriedAddressDialog from '@/modules/accounts/QueriedAddressDialog.vue';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { type Module, SUPPORTED_MODULES, type SupportedModule } from '@/modules/core/common/modules';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import ModuleAddressesCell from '@/modules/settings/modules/ModuleAddressesCell.vue';
import { useModuleToggle } from '@/modules/settings/modules/use-module-toggle';
import { useSetting } from '@/modules/settings/use-setting';
import IconMark from '@/modules/shell/components/IconMark.vue';

type ModuleEntry = SupportedModule & { enabled: boolean };

const { t } = useI18n({ useScope: 'global' });

const supportedModules = SUPPORTED_MODULES;
const search = ref<string>('');
const manageModule = ref<Module>();

const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { fetchQueriedAddresses } = useQueriedAddressOperations();
const activeModules = useSetting('activeModules');
const { disableAll, enableAll, loading, switchModule } = useModuleToggle(activeModules);

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
