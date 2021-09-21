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
          $tc('loan_collateral.watchers.edit', watchers.length, {
            n: watchers.length
          })
        }}
      </span>
      <span v-else class="text-caption">
        {{ $t('loan_collateral.watchers.add') }}
      </span>
      <premium-lock v-if="!premium" size="x-small" />
    </v-btn>
    <watcher-dialog
      :display="showWatcherDialog"
      :title="$t('loan_collateral.watchers.dialog.title')"
      :message="watcherMessage"
      :watcher-content-id="vault.identifier"
      :existing-watchers="watchers"
      preselect-watcher-type="makervault_collateralization_ratio"
      :watcher-value-label="$t('loan_collateral.watchers.dialog.label')"
      @cancel="showWatcherDialog = false"
    />
  </fragment>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import WatcherDialog from '@/components/dialogs/WatcherDialog.vue';
import Fragment from '@/components/helper/Fragment';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { setupThemeCheck } from '@/composables/common';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { MakerDAOVaultModel } from '@/store/defi/types';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'ManageWatchers',
  components: { Fragment, PremiumLock, WatcherDialog },
  props: {
    vault: {
      required: true,
      type: Object as PropType<MakerDAOVaultModel>
    }
  },
  setup(props) {
    const showWatcherDialog = ref(false);
    const watcherMessage = ref('');
    const { vault } = toRefs(props);
    const store = useStore();
    const loanWatchers = computed(() => store.state.session!!.watchers);
    const premium = getPremium();
    const watchers = computed(() => {
      const { identifier } = vault.value;
      return loanWatchers.value.filter(watcher => {
        const watcherArgs = watcher.args;

        if (watcherArgs.vault_id.indexOf(identifier) > -1) return watcher;
      });
    });

    const openWatcherDialog = () => {
      if (!premium.value) {
        return;
      }

      const { collateralizationRatio, identifier, liquidationRatio } =
        vault.value;
      const params = {
        collateralizationRatio,
        identifier,
        liquidationRatio
      };
      showWatcherDialog.value = true;
      watcherMessage.value = i18n
        .t('loan_collateral.watchers.dialog.message', params)
        .toString();
    };

    const { dark } = setupThemeCheck();

    return {
      showWatcherDialog,
      openWatcherDialog,
      watcherMessage,
      watchers,
      premium,
      dark
    };
  }
});
</script>
