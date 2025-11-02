<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { LidoCsmNodeOperator, LidoCsmNodeOperatorPayload } from '@/types/staking';
import { BigNumber, bigNumberify, Blockchain } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useLidoCsmApi } from '@/composables/api/staking/lido-csm';
import { useMessageStore } from '@/store/message';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

defineOptions({
  name: 'LidoCsmPage',
});

const { t } = useI18n({ useScope: 'global' });
const { isDark } = useRotkiTheme();

const STETH_IDENTIFIER = 'eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84';

const nodeOperators = ref<LidoCsmNodeOperator[]>([]);
const loading = ref<boolean>(false);
const selectedAccount = ref<BlockchainAccount<AddressData>[]>([]);
const nodeOperatorId = ref<string>('');
const submitting = ref<boolean>(false);
const removingEntryKey = ref<string>('');
const dialogOpen = ref<boolean>(false);

const api = useLidoCsmApi();
const { setMessage } = useMessageStore();

const selectedAddress = computed<string>(() => {
  const account = get(selectedAccount)[0];
  return account ? getAccountAddress(account) : '';
});

const nodeOperatorInputError = computed<string | undefined>(() => {
  const value = get(nodeOperatorId).trim();
  if (value === '')
    return undefined;

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0)
    return t('staking_page.lido_csm.form.validation.invalid_id');

  return undefined;
});

const nodeOperatorInputErrors = computed<string[]>(() => {
  const error = get(nodeOperatorInputError);
  return error ? [error] : [];
});

const formValid = computed<boolean>(() => {
  if (get(nodeOperatorInputError))
    return false;

  return get(selectedAddress) !== '' && get(nodeOperatorId).trim() !== '';
});

const notAvailableLabel = computed<string>(() => t('staking_page.lido_csm.table.not_available'));
const dialogDescription = computed<string>(() => t('staking_page.lido_csm.form.description'));

function toErrorMessage(error: unknown): string {
  if (error instanceof Error)
    return error.message;

  return String(error);
}

function toBigNumberValue(value?: BigNumber | string | number | null): BigNumber | null {
  if (value === undefined || value === null)
    return null;

  return BigNumber.isBigNumber(value) ? value : bigNumberify(value);
}

async function fetchNodeOperators(): Promise<void> {
  set(loading, true);
  try {
    const { entries, message } = await api.listNodeOperators();
    set(nodeOperators, entries);
    notifyWarning(message);
  }
  catch (error: unknown) {
    setMessage({
      description: t('staking_page.lido_csm.messages.fetch_failed', { message: toErrorMessage(error) }),
    });
  }
  finally {
    set(loading, false);
  }
}

async function refreshAllNodeOperators(): Promise<void> {
  set(loading, true);
  try {
    const { entries, message } = await api.refreshMetrics();
    set(nodeOperators, entries);
    notifyWarning(message);
  }
  catch (error: unknown) {
    setMessage({
      description: t('staking_page.lido_csm.messages.refresh_failed', { message: toErrorMessage(error) }),
    });
  }
  finally {
    set(loading, false);
  }
}

async function addNodeOperator(payload: LidoCsmNodeOperatorPayload): Promise<void> {
  try {
    const { entries, message } = await api.addNodeOperator(payload);
    set(nodeOperators, entries);
    notifyWarning(message);
  }
  catch (error: unknown) {
    setMessage({
      description: t('staking_page.lido_csm.messages.add_failed', { message: toErrorMessage(error) }),
    });
    throw error;
  }
}

async function deleteNodeOperator(payload: LidoCsmNodeOperatorPayload): Promise<void> {
  try {
    const { entries, message } = await api.deleteNodeOperator(payload);
    set(nodeOperators, entries);
    notifyWarning(message);
  }
  catch (error: unknown) {
    setMessage({
      description: t('staking_page.lido_csm.messages.delete_failed', { message: toErrorMessage(error) }),
    });
    throw error;
  }
}

function formatCount(value?: number | null): string {
  if (value === undefined || value === null)
    return get(notAvailableLabel);

  return value.toString();
}

function notifyWarning(message?: string): void {
  if (!message)
    return;

  setMessage({
    description: message,
  });
}

interface LidoCsmTableRow {
  key: string;
  address: string;
  nodeOperatorId: number;
  operatorTypeLabel: string;
  operatorTypeId: number | null;
  bondCurrent: BigNumber | null;
  bondRequired: BigNumber | null;
  bondClaimable: BigNumber | null;
  totalDeposited: string;
  rewardsPending: BigNumber | null;
}

const tableRows = computed<LidoCsmTableRow[]>(() => get(nodeOperators).map((entry) => {
  const metrics = entry.metrics;
  const operatorType = metrics?.operatorType;
  const bond = metrics?.bond;
  const keys = metrics?.keys;
  const rewards = metrics?.rewards;

  return {
    address: entry.address,
    bondClaimable: toBigNumberValue(bond?.claimable ?? null),
    bondCurrent: toBigNumberValue(bond?.current ?? null),
    bondRequired: toBigNumberValue(bond?.required ?? null),
    key: `${entry.address}-${entry.nodeOperatorId}`,
    nodeOperatorId: entry.nodeOperatorId,
    operatorTypeId: operatorType?.id ?? null,
    operatorTypeLabel: operatorType?.label ?? get(notAvailableLabel),
    rewardsPending: toBigNumberValue(rewards?.pending ?? null),
    totalDeposited: formatCount(keys?.totalDeposited ?? null),
  };
}));

const tableColumns = computed<DataTableColumn<LidoCsmTableRow>[]>(() => [{
  key: 'address',
  label: t('staking_page.lido_csm.table.address'),
}, {
  key: 'nodeOperatorId',
  label: t('staking_page.lido_csm.table.node_operator'),
}, {
  key: 'operatorTypeLabel',
  label: t('staking_page.lido_csm.table.operator_type'),
}, {
  key: 'bondCurrent',
  label: t('staking_page.lido_csm.table.bond_current'),
}, {
  key: 'bondRequired',
  label: t('staking_page.lido_csm.table.bond_required'),
}, {
  key: 'bondClaimable',
  label: t('staking_page.lido_csm.table.bond_claimable'),
}, {
  key: 'totalDeposited',
  label: t('staking_page.lido_csm.table.keys_total'),
}, {
  key: 'rewardsPending',
  label: t('staking_page.lido_csm.table.rewards_pending'),
}, {
  align: 'end',
  key: 'actions',
  label: t('staking_page.lido_csm.table.actions'),
}]);

const hasEntries = computed<boolean>(() => get(tableRows).length > 0);

function resetForm(): void {
  set(selectedAccount, []);
  set(nodeOperatorId, '');
}

function resetDialogState(): void {
  resetForm();
}

function closeDialog(): void {
  set(dialogOpen, false);
}

function openAddDialog(): void {
  resetDialogState();
  set(dialogOpen, true);
}

async function submitForm(): Promise<void> {
  if (!get(formValid) || get(submitting))
    return;

  set(submitting, true);
  try {
    await addNodeOperator({
      address: get(selectedAddress),
      nodeOperatorId: Number(get(nodeOperatorId)),
    });

    closeDialog();
  }
  finally {
    set(submitting, false);
  }
}

async function handleRemove(address: string, nodeOperatorIdValue: number): Promise<void> {
  const key = `${address}-${nodeOperatorIdValue}`;
  if (get(removingEntryKey) === key)
    return;

  set(removingEntryKey, key);
  try {
    await deleteNodeOperator({
      address,
      nodeOperatorId: nodeOperatorIdValue,
    });
  }
  finally {
    set(removingEntryKey, '');
  }
}

async function handleRefresh(): Promise<void> {
  if (get(loading))
    return;

  await refreshAllNodeOperators();
}

watch(dialogOpen, (isOpen) => {
  if (!isOpen)
    resetDialogState();
});

onMounted(async () => {
  if (get(nodeOperators).length === 0)
    await fetchNodeOperators();
});

defineExpose({
  refresh: handleRefresh,
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking_page.lido_csm.title')]"
    child
  >
    <template #buttons>
      <RuiButton
        color="primary"
        :disabled="loading"
        @click="openAddDialog()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="18"
          />
        </template>
        {{ t('staking_page.lido_csm.form.submit') }}
      </RuiButton>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading"
            @click="handleRefresh()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('staking_page.lido_csm.table.refresh_tooltip') }}
      </RuiTooltip>
    </template>
    <div class="flex flex-col gap-6">
      <div>
        <p class="text-sm text-rui-text-secondary">
          {{ t('staking_page.lido_csm.description') }}
        </p>
      </div>

      <RuiCard>
        <div
          v-if="loading"
          class="space-y-3"
        >
          <RuiSkeletonLoader
            v-for="i in 3"
            :key="i"
            class="h-12"
          />
        </div>
        <div
          v-else-if="!hasEntries"
          class="flex flex-col items-center text-center text-rui-text-secondary py-8"
        >
          <img
            :src="isDark ? '/assets/images/placeholder/table_no_data_placeholder_dark.svg' : '/assets/images/placeholder/table_no_data_placeholder.svg'"
            :alt="t('staking_page.lido_csm.table.empty')"
            class="h-32"
          />
          {{ t('staking_page.lido_csm.table.empty') }}
        </div>
        <div
          v-else
          class="space-y-4 overflow-x-auto"
        >
          <p class="text-sm text-rui-text-secondary">
            {{ t('staking_page.lido_csm.table.description') }}
          </p>
          <RuiDataTable
            dense
            outlined
            class="min-w-full"
            row-attr="key"
            :cols="tableColumns"
            :rows="tableRows"
          >
            <template #item.address="{ row }">
              <span class="font-mono break-all text-sm">
                {{ row.address }}
              </span>
            </template>
            <template #item.nodeOperatorId="{ row }">
              <span class="text-sm">
                {{ row.nodeOperatorId }}
              </span>
            </template>
            <template #item.operatorTypeLabel="{ row }">
              <span class="font-medium text-sm">
                {{ row.operatorTypeLabel }}
              </span>
            </template>
            <template #item.bondCurrent="{ row }">
              <div
                v-if="row.bondCurrent"
                class="flex items-center gap-2 text-sm"
              >
                <AssetIcon
                  :identifier="STETH_IDENTIFIER"
                  size="20px"
                  no-tooltip
                />
                <AmountDisplay
                  show-currency="ticker"
                  force-currency
                  :asset="STETH_IDENTIFIER"
                  :value="row.bondCurrent"
                />
              </div>
              <span
                v-else
                class="text-sm text-rui-text-secondary"
              >
                {{ notAvailableLabel }}
              </span>
            </template>
            <template #item.bondRequired="{ row }">
              <div
                v-if="row.bondRequired"
                class="flex items-center gap-2 text-sm"
              >
                <AssetIcon
                  :identifier="STETH_IDENTIFIER"
                  size="20px"
                  no-tooltip
                />
                <AmountDisplay
                  show-currency="ticker"
                  force-currency
                  :asset="STETH_IDENTIFIER"
                  :value="row.bondRequired"
                />
              </div>
              <span
                v-else
                class="text-sm text-rui-text-secondary"
              >
                {{ notAvailableLabel }}
              </span>
            </template>
            <template #item.bondClaimable="{ row }">
              <div
                v-if="row.bondClaimable"
                class="flex items-center gap-2 text-sm"
              >
                <AssetIcon
                  :identifier="STETH_IDENTIFIER"
                  size="20px"
                  no-tooltip
                />
                <AmountDisplay
                  show-currency="ticker"
                  force-currency
                  :asset="STETH_IDENTIFIER"
                  :value="row.bondClaimable"
                />
              </div>
              <span
                v-else
                class="text-sm text-rui-text-secondary"
              >
                {{ notAvailableLabel }}
              </span>
            </template>
            <template #item.totalDeposited="{ row }">
              <span class="text-sm">
                {{ row.totalDeposited }}
              </span>
            </template>
            <template #item.rewardsPending="{ row }">
              <div
                v-if="row.rewardsPending"
                class="flex items-center gap-2 text-sm"
              >
                <AssetIcon
                  :identifier="STETH_IDENTIFIER"
                  size="20px"
                  no-tooltip
                />
                <AmountDisplay
                  show-currency="ticker"
                  force-currency
                  :asset="STETH_IDENTIFIER"
                  :value="row.rewardsPending"
                />
              </div>
              <span
                v-else
                class="text-sm text-rui-text-secondary"
              >
                {{ notAvailableLabel }}
              </span>
            </template>
            <template #item.actions="{ row }">
              <div class="flex justify-end gap-1">
                <RuiButton
                  color="error"
                  variant="text"
                  size="sm"
                  :loading="removingEntryKey === row.key"
                  @click="handleRemove(row.address, row.nodeOperatorId)"
                >
                  {{ t('staking_page.lido_csm.table.remove') }}
                </RuiButton>
              </div>
            </template>
          </RuiDataTable>
        </div>
      </RuiCard>

      <RuiDialog
        v-model="dialogOpen"
        max-width="520"
      >
        <RuiCard
          divide
          no-padding
          content-class="overflow-hidden"
        >
          <template #header>
            {{ t('staking_page.lido_csm.form.title') }}
          </template>
          <RuiButton
            variant="text"
            class="absolute top-2 right-2"
            icon
            @click="closeDialog()"
          >
            <RuiIcon
              class="text-white"
              name="lu-x"
            />
          </RuiButton>
          <div class="p-4 space-y-6">
            <p class="text-sm text-rui-text-secondary">
              {{ dialogDescription }}
            </p>
            <div class="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <BlockchainAccountSelector
                v-model="selectedAccount"
                :chains="[Blockchain.ETH]"
                outlined
                :label="t('staking_page.lido_csm.form.address_label')"
                :custom-hint="t('staking_page.lido_csm.form.address_hint')"
              />
              <RuiTextField
                v-model="nodeOperatorId"
                type="number"
                min="0"
                step="1"
                color="primary"
                :label="t('staking_page.lido_csm.form.node_operator_label')"
                :hint="t('staking_page.lido_csm.form.node_operator_hint')"
                :error-messages="nodeOperatorInputErrors"
                variant="outlined"
              />
            </div>
          </div>
          <template #footer>
            <div class="w-full flex justify-end gap-2 pt-2">
              <RuiButton
                variant="text"
                @click="closeDialog()"
              >
                {{ t('common.actions.cancel') }}
              </RuiButton>
              <RuiButton
                color="primary"
                :loading="submitting"
                :disabled="!formValid"
                @click="submitForm()"
              >
                {{ t('staking_page.lido_csm.form.submit') }}
              </RuiButton>
            </div>
          </template>
        </RuiCard>
      </RuiDialog>
    </div>
  </TablePageLayout>
</template>
