<template>
  <fragment>
    <v-btn
      small
      rounded
      block
      depressed
      :color="dark ? null : 'grey lighten-3 grey--text text--darken-2'"
      class="text-decoration-none"
      @click="openWatcherDialog"
    >
      <v-icon x-small left>mdi-bell-outline</v-icon>
      <span v-if="watchers.length > 0" class="text-caption">
        {{
          tc('loan_collateral.watchers.edit', watchers.length, {
            n: watchers.length
          })
        }}
      </span>
      <span v-else class="text-caption">
        {{ tc('loan_collateral.watchers.add') }}
      </span>
      <premium-lock v-if="!premium" x-small />
    </v-btn>
    <watcher-dialog
      :display="showWatcherDialog"
      :title="tc('loan_collateral.watchers.dialog.title')"
      :message="watcherMessage"
      :watcher-content-id="vault.identifier"
      :existing-watchers="watchers"
      preselect-watcher-type="makervault_collateralization_ratio"
      :watcher-value-label="tc('loan_collateral.watchers.dialog.label')"
      @cancel="showWatcherDialog = false"
    />
  </fragment>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import WatcherDialog from '@/components/dialogs/WatcherDialog.vue';
import Fragment from '@/components/helper/Fragment';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { useTheme } from '@/composables/common';
import { usePremium } from '@/composables/premium';
import { useWatchersStore } from '@/store/session/watchers';
import { MakerDAOVaultModel } from '@/types/defi/maker';

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
const { tc } = useI18n();
const watchers = computed(() => {
  const { identifier } = get(vault);
  return get(loanWatchers).filter(watcher => {
    const watcherArgs = watcher.args;

    if (watcherArgs.vault_id.indexOf(identifier) > -1) return watcher;
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
  set(watcherMessage, tc('loan_collateral.watchers.dialog.message', 0, params));
};

const { dark } = useTheme();
</script>
