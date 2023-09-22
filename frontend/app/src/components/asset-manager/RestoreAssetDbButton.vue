<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { DialogType } from '@/types/dialogs';

withDefaults(
  defineProps<{
    dropdown?: boolean;
  }>(),
  { dropdown: false }
);

type ResetType = 'soft' | 'hard';

const { notify } = useNotificationsStore();
const { connect, setConnected } = useMainStore();
const { logout } = useSessionStore();
const { restoreAssetsDatabase } = useAssetsApi();

const { restartBackend } = useBackendManagement();

const { t } = useI18n();

async function restoreAssets(resetType: ResetType) {
  try {
    const updated = await restoreAssetsDatabase(
      resetType,
      resetType === 'hard'
    );
    if (updated) {
      showDoneConfirmation();
    }
  } catch (e: any) {
    const title = t('asset_update.restore.title').toString();
    const message = e.toString();
    if (message.includes('There are assets that can not')) {
      showDoubleConfirmation(resetType);
    }
    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true
    });
  }
}

const { navigateToUserLogin } = useAppNavigation();

async function updateComplete() {
  await logout();
  await navigateToUserLogin();
  setConnected(false);
  await restartBackend();
  await connect();
}

const { show } = useConfirmStore();

const showRestoreConfirmation = (type: ResetType) => {
  show(
    {
      title: t('asset_update.restore.delete_confirmation.title'),
      message:
        type === 'soft'
          ? t('asset_update.restore.delete_confirmation.soft_reset_message')
          : t('asset_update.restore.delete_confirmation.hard_reset_message')
    },
    () => restoreAssets(type)
  );
};

const showDoubleConfirmation = (type: ResetType) => {
  show(
    {
      title: t('asset_update.restore.hard_restore_confirmation.title'),
      message: t('asset_update.restore.hard_restore_confirmation.message')
    },
    () => restoreAssets(type)
  );
};

const showDoneConfirmation = () => {
  show(
    {
      title: t('asset_update.restore.success.title'),
      message: t('asset_update.restore.success.description'),
      primaryAction: t('asset_update.success.ok'),
      singleAction: true,
      type: DialogType.SUCCESS
    },
    updateComplete
  );
};
</script>

<template>
  <div>
    <template v-if="dropdown">
      <VMenu offset-y>
        <template #activator="{ on }">
          <RuiButton color="primary" v-on="on">
            {{ t('asset_update.restore.title') }}
          </RuiButton>
        </template>
        <VList>
          <VListItem two-line link @click="showRestoreConfirmation('soft')">
            <VListItemContent>
              <VListItemTitle>
                {{ t('asset_update.restore.soft_reset') }}
              </VListItemTitle>
              <VListItemSubtitle>
                {{ t('asset_update.restore.soft_reset_hint') }}
              </VListItemSubtitle>
            </VListItemContent>
          </VListItem>
          <VListItem two-line link @click="showRestoreConfirmation('hard')">
            <VListItemContent>
              <VListItemTitle>
                {{ t('asset_update.restore.hard_reset') }}
              </VListItemTitle>
              <VListItemSubtitle>
                {{ t('asset_update.restore.hard_reset_hint') }}
              </VListItemSubtitle>
            </VListItemContent>
          </VListItem>
        </VList>
      </VMenu>
    </template>
    <template v-else>
      <VTooltip top max-width="200">
        <template #activator="{ on }">
          <RuiButton
            color="primary"
            v-on="on"
            @click="showRestoreConfirmation('soft')"
          >
            {{ t('asset_update.restore.soft_reset') }}
          </RuiButton>
        </template>
        <span>{{ t('asset_update.restore.soft_reset_hint') }}</span>
      </VTooltip>
      <VTooltip top max-width="200">
        <template #activator="{ on }">
          <RuiButton
            class="ml-4"
            color="primary"
            v-on="on"
            @click="showRestoreConfirmation('hard')"
          >
            {{ t('asset_update.restore.hard_reset') }}
          </RuiButton>
        </template>
        <span>{{ t('asset_update.restore.hard_reset_hint') }}</span>
      </VTooltip>
    </template>
  </div>
</template>
