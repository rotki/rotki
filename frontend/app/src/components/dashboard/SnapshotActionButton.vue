<script setup lang="ts">
import SnapshotImportDialog from '@/components/dashboard/SnapshotImportDialog.vue';
import type { Writeable } from '@rotki/common';
import type { AllBalancePayload } from '@/types/blockchain/accounts';

const ignoreErrors = ref<boolean>(false);
const visible = ref<boolean>(false);
const balanceSnapshotFile = ref<File>();
const locationDataSnapshotFile = ref<File>();
const importSnapshotLoading = ref<boolean>(false);
const importSnapshotDialog = ref<boolean>(false);

const { t } = useI18n();
const premium = usePremium();
const { logout } = useSessionStore();
const { lastBalanceSave } = storeToRefs(usePeriodicStore());
const { fetchBalances } = useBalances();
const { getPath } = useInterop();
const { fetchNetValue } = useStatisticsStore();
const { setMessage } = useMessageStore();
const { importBalancesSnapshot, uploadBalancesSnapshot } = useSnapshotApi();
const { isDark } = useRotkiTheme();

async function refreshAllAndSave() {
  set(visible, false);
  const payload: Writeable<Partial<AllBalancePayload>> = {
    ignoreCache: true,
    saveData: true,
  };
  if (get(ignoreErrors))
    payload.ignoreErrors = true;

  await fetchBalances(payload);
  await fetchNetValue();
}

async function importSnapshot() {
  if (!(isDefined(balanceSnapshotFile) && isDefined(locationDataSnapshotFile)))
    return;

  set(importSnapshotLoading, true);

  const balanceFile = get(balanceSnapshotFile);
  const locationFile = get(locationDataSnapshotFile);

  let success = false;
  let message = '';
  try {
    const balanceFilePath = getPath(balanceFile);
    const locationFilePath = getPath(locationFile);
    if (balanceFilePath && locationFilePath)
      await importBalancesSnapshot(balanceFilePath, locationFilePath);
    else
      await uploadBalancesSnapshot(balanceFile, locationFile);

    success = true;
  }
  catch (error: any) {
    message = error.message;
  }

  if (!success) {
    setMessage({
      title: t('snapshot_action_button.messages.title'),
      description: t('snapshot_action_button.messages.failed_description', {
        message,
      }),
    });
  }
  else {
    setMessage({
      title: t('snapshot_action_button.messages.title'),
      description: t('snapshot_action_button.messages.success_description', {
        message,
      }),
      success: true,
    });

    setTimeout(() => {
      startPromise(logout());
    }, 3000);
  }

  set(importSnapshotLoading, false);
  set(balanceSnapshotFile, null);
  set(locationDataSnapshotFile, null);
}
</script>

<template>
  <RuiMenu
    id="snapshot-action-menu"
    v-model="visible"
    :popper="{ placement: 'bottom-end' }"
    :persistent="importSnapshotDialog"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('snapshot_action_button.menu_tooltip', premium ? 2 : 1)"
        :variant="!isDark ? 'default' : 'text'"
        size="sm"
        custom-color
        v-bind="attrs"
      >
        <slot name="button-icon">
          <RuiIcon name="screenshot-2-line" />
        </slot>
      </MenuTooltipButton>
    </template>
    <div class="p-4 md:w-[16rem] w-full">
      <div class="font-medium">
        {{ t('snapshot_action_button.snapshot_title') }}
      </div>

      <div class="pt-2 text-rui-text-secondary">
        <DateDisplay
          v-if="lastBalanceSave"
          :timestamp="lastBalanceSave"
        />

        <span v-else>
          {{ t('common.never') }}
        </span>
      </div>

      <RuiDivider class="my-4" />

      <div class="flex flex-row items-center gap-4">
        <RuiButton
          color="primary"
          variant="outlined"
          @click="refreshAllAndSave()"
        >
          <template #prepend>
            <RuiIcon name="save-line" />
          </template>
          {{ t('snapshot_action_button.force_save') }}
        </RuiButton>

        <RuiTooltip
          :open-delay="400"
          tooltip-class="max-w-[16rem]"
        >
          <template #activator>
            <RuiIcon
              name="information-line"
              color="primary"
            />
          </template>
          {{ t('snapshot_action_button.snapshot_tooltip') }}
        </RuiTooltip>
      </div>

      <RuiTooltip
        class="mt-2"
        :open-delay="400"
        tooltip-class="max-w-[16rem]"
      >
        <template #activator>
          <RuiCheckbox
            v-model="ignoreErrors"
            color="primary"
            hide-details
          >
            {{ t('snapshot_action_button.ignore_errors_label') }}
          </RuiCheckbox>
        </template>
        {{ t('snapshot_action_button.ignore_errors_tooltip') }}
      </RuiTooltip>

      <RuiDivider class="mb-4" />

      <div>
        <div class="font-medium pb-2">
          {{ t('snapshot_import_dialog.title') }}
        </div>
        <SnapshotImportDialog
          v-model="importSnapshotDialog"
          :balance-file="balanceSnapshotFile"
          :location-file="locationDataSnapshotFile"
          :loading="importSnapshotLoading"
          @import="importSnapshot()"
          @update:balance-file="balanceSnapshotFile = $event"
          @update:location-file="locationDataSnapshotFile = $event"
        />
      </div>
    </div>
  </RuiMenu>
</template>
