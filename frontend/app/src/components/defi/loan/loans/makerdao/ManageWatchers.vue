<script setup lang="ts">
import { type PropType } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps({
  vault: {
    required: true,
    type: Object as PropType<MakerDAOVaultModel>
  }
});

const showWatcherDialog = ref(false);
const watcherMessage = ref('');
const { vault } = toRefs(props);
const { watchers: loanWatchers } = storeToRefs(useWatchersStore());
const premium = usePremium();
const { t } = useI18n();
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

const { dark } = useTheme();
</script>

<template>
  <Fragment>
    <VBtn
      small
      rounded
      block
      depressed
      :color="dark ? null : 'grey lighten-3 grey--text text--darken-2'"
      class="text-decoration-none"
      @click="openWatcherDialog()"
    >
      <VIcon x-small left>mdi-bell-outline</VIcon>
      <span v-if="watchers.length > 0" class="text-caption">
        {{
          t(
            'loan_collateral.watchers.edit',
            {
              n: watchers.length
            },
            watchers.length
          )
        }}
      </span>
      <span v-else class="text-caption">
        {{ t('loan_collateral.watchers.add') }}
      </span>
      <PremiumLock v-if="!premium" x-small />
    </VBtn>
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
  </Fragment>
</template>
