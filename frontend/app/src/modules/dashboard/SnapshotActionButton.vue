<script setup lang="ts">
import type { Writeable } from '@rotki/common';
import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { useLogout } from '@/modules/auth/use-logout';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import SnapshotImportDialog from '@/modules/dashboard/SnapshotImportDialog.vue';
import { usePremium } from '@/modules/premium/use-premium';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

const ignoreErrors = ref<boolean>(false);
const visible = ref<boolean>(false);
const balanceSnapshotFile = ref<File>();
const locationDataSnapshotFile = ref<File>();
const importSnapshotLoading = ref<boolean>(false);
const importSnapshotDialog = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();
const { logout } = useLogout();
const { lastBalanceSave } = storeToRefs(useSessionMetadataStore());
const { fetchBalances } = useBalanceFetching();
const { getPath } = useInterop();
const { fetchNetValue } = useStatisticsDataFetching();
const { setMessage } = useMessageStore();
const { importBalancesSnapshot, uploadBalancesSnapshot } = useSnapshotApi();
const { ignoreSnapshotError } = storeToRefs(useFrontendSettingsStore());

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
  catch (error: unknown) {
    message = getErrorMessage(error);
  }

  if (!success) {
    setMessage({
      description: t('snapshot_action_button.messages.failed_description', {
        message,
      }),
      title: t('snapshot_action_button.messages.title'),
    });
  }
  else {
    setMessage({
      description: t('snapshot_action_button.messages.success_description', {
        message,
      }),
      success: true,
      title: t('snapshot_action_button.messages.title'),
    });

    setTimeout(() => {
      startPromise(logout());
    }, 3000);
  }

  set(importSnapshotLoading, false);
  set(balanceSnapshotFile, null);
  set(locationDataSnapshotFile, null);
}

watchImmediate(ignoreSnapshotError, (ignoreSnapshotError) => {
  set(ignoreErrors, ignoreSnapshotError);
});
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
        variant="default"
        size="sm"
        custom-color
        v-bind="attrs"
        class="!p-2"
      >
        <RuiIcon name="lu-git-commit-vertical" />
      </MenuTooltipButton>
    </template>
    <div class="p-4 md:w-[16rem] w-full">
      <div class="font-medium">
        {{ t('snapshot_action_button.snapshot_title') }}
      </div>

      <div class="pt-0.5 text-sm text-rui-text-secondary">
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
            <RuiIcon name="lu-save" />
          </template>
          {{ t('snapshot_action_button.force_save') }}
        </RuiButton>

        <RuiTooltip
          :open-delay="400"
          tooltip-class="max-w-[16rem]"
        >
          <template #activator>
            <RuiIcon
              name="lu-info"
              size="18"
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
          <SettingsOption
            #default="{ error, success, updateImmediate }"
            setting="ignoreSnapshotError"
            frontend-setting
          >
            <RuiCheckbox
              v-model="ignoreErrors"
              color="primary"
              :error-messages="error"
              :success-messages="success"
              hide-details
              @update:model-value="updateImmediate($event)"
            >
              {{ t('snapshot_action_button.ignore_errors_label') }}
            </RuiCheckbox>
          </SettingsOption>
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
          v-model:balance-file="balanceSnapshotFile"
          v-model:location-file="locationDataSnapshotFile"
          :loading="importSnapshotLoading"
          @import="importSnapshot()"
        />
      </div>
    </div>
  </RuiMenu>
</template>
