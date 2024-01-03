<script setup lang="ts">
import { type Writeable } from '@/types';
import { type AllBalancePayload } from '@/types/blockchain/accounts';
import SnapshotImportDialog from '@/components/dashboard/SnapshotImportDialog.vue';

const ignoreErrors = ref<boolean>(false);
const visible = ref<boolean>(false);
const balanceSnapshotFile = ref<File | null>(null);
const locationDataSnapshotFile = ref<File | null>(null);
const importSnapshotLoading = ref<boolean>(false);
const importSnapshotDialog = ref<boolean>(false);

const { t } = useI18n();
const premium = usePremium();
const { logout } = useSessionStore();
const { lastBalanceSave } = storeToRefs(usePeriodicStore());
const { fetchBalances } = useBalances();
const { appSession } = useInterop();
const { fetchNetValue } = useStatisticsStore();
const { setMessage } = useMessageStore();
const { importBalancesSnapshot, uploadBalancesSnapshot } = useSnapshotApi();
const { dark } = useTheme();

const refreshAllAndSave = async () => {
  set(visible, false);
  const payload: Writeable<Partial<AllBalancePayload>> = {
    ignoreCache: true,
    saveData: true
  };
  if (get(ignoreErrors)) {
    payload.ignoreErrors = true;
  }
  await fetchBalances(payload);
  await fetchNetValue();
};

const importSnapshot = async () => {
  set(importSnapshotLoading, true);

  let success = false;
  let message = '';
  try {
    if (appSession) {
      await importBalancesSnapshot(
        get(balanceSnapshotFile)!.path,
        get(locationDataSnapshotFile)!.path
      );
    } else {
      await uploadBalancesSnapshot(
        get(balanceSnapshotFile)!,
        get(locationDataSnapshotFile)!
      );
    }
    success = true;
  } catch (e: any) {
    message = e.message;
  }

  if (!success) {
    setMessage({
      title: t('snapshot_action_button.messages.title'),
      description: t('snapshot_action_button.messages.failed_description', {
        message
      })
    });
  } else {
    setMessage({
      title: t('snapshot_action_button.messages.title'),
      description: t('snapshot_action_button.messages.success_description', {
        message
      }),
      success: true
    });

    setTimeout(() => {
      startPromise(logout());
    }, 3000);
  }

  set(importSnapshotLoading, false);
  set(balanceSnapshotFile, null);
  set(locationDataSnapshotFile, null);
};
</script>

<template>
  <VMenu
    id="snapshot-action-menu"
    v-model="visible"
    left
    transition="slide-y-transition"
    :close-on-content-click="false"
    z-index="215"
  >
    <template #activator="{ on }">
      <MenuTooltipButton
        :tooltip="t('snapshot_action_button.menu_tooltip', premium ? 2 : 1)"
        :variant="!dark ? 'default' : 'text'"
        size="sm"
        v-on="on"
      >
        <slot name="button-icon">
          <RuiIcon name="screenshot-2-line" />
        </slot>
      </MenuTooltipButton>
    </template>
    <div class="p-4 md:w-[15.625rem] w-full">
      <div class="font-medium">
        {{ t('snapshot_action_button.snapshot_title') }}
      </div>

      <div class="pt-2 text--secondary">
        <DateDisplay v-if="lastBalanceSave" :timestamp="lastBalanceSave" />

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

        <RuiTooltip :open-delay="400" tooltip-class="max-w-[16rem]">
          <template #activator>
            <RuiIcon name="information-line" color="primary" />
          </template>
          {{ t('snapshot_action_button.snapshot_tooltip') }}
        </RuiTooltip>
      </div>

      <RuiTooltip class="mt-2" :open-delay="400" tooltip-class="max-w-[16rem]">
        <template #activator>
          <RuiCheckbox v-model="ignoreErrors" color="primary" hide-details>
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
  </VMenu>
</template>
