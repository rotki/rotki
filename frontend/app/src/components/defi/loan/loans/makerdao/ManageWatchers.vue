<script setup lang="ts">
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps<{
  vault: MakerDAOVaultModel;
}>();

const { t } = useI18n();

const { vault } = toRefs(props);

const showWatcherDialog = ref(false);
const watcherMessage = ref('');

const { watchers: loanWatchers } = storeToRefs(useWatchersStore());
const premium = usePremium();

const watchers = computed(() => {
  const { identifier } = get(vault);
  return get(loanWatchers).filter(watcher => {
    const watcherArgs = watcher.args;
    return watcherArgs.vaultId.includes(identifier);
  });
});

const openWatcherDialog = () => {
  if (!get(premium)) {
    return;
  }

  const { collateralizationRatio, identifier, liquidationRatio } = get(vault);
  const params = {
    collateralizationRatio,
    identifier,
    liquidationRatio
  };
  set(showWatcherDialog, true);
  set(watcherMessage, t('loan_collateral.watchers.dialog.message', params));
};
</script>

<template>
  <div class="flex items-center gap-2">
    <span v-if="!premium">
      <PremiumLock />
    </span>
    <RuiButton
      color="primary"
      :disabled="!premium"
      class="w-full py-2"
      @click="openWatcherDialog()"
    >
      <template #prepend>
        <RuiIcon class="my-1" name="notification-line" />
      </template>

      <template v-if="watchers.length > 0">
        {{
          t(
            'loan_collateral.watchers.edit',
            {
              n: watchers.length
            },
            watchers.length
          )
        }}
      </template>
      <template v-else>
        {{ t('loan_collateral.watchers.add') }}
      </template>
    </RuiButton>

    <WatcherDialog
      :display="showWatcherDialog"
      :title="t('loan_collateral.watchers.dialog.title')"
      :message="watcherMessage"
      :watcher-content-id="vault.identifier"
      :existing-watchers="watchers"
      preselect-watcher-type="makervault_collateralization_ratio"
      :watcher-value-label="t('loan_collateral.watchers.dialog.label')"
      @cancel="showWatcherDialog = false"
    />
  </div>
</template>
