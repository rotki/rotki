<script setup lang="ts">
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { accountHistoryParams, toAccountHistoryFields } from '@/modules/balances/account-history/account-history-fields';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { useDataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';

const account = defineModel<string | undefined>('account', { required: true });
const asset = defineModel<string | undefined>('asset', { required: true });
const location = defineModel<string | undefined>('location', { required: true });

const { assets, assetsProcessingRequired = false, locations, restrictAssets = true } = defineProps<{
  /** The assets the account has ever held; the asset pill offers only these. */
  assets: string[];
  /** Offer only `assets`. Off without premium, where the list cannot be loaded and any asset is searched. */
  restrictAssets?: boolean;
  /** The account's events are not all processed yet, so `assets` may be missing some. */
  assetsProcessingRequired?: boolean;
  /** The locations the account held the asset in; offered as a pill only with the held list. */
  locations: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const shared = useSharedFieldResolvers();
const accounts = useDataIssueAccountOptions();
const { assetSearch } = useAssetInfoRetrieval();
const searchAsset = assetSuggestions(assetSearch);
const pillLabels = usePillBarLabels();

/** Built inside a computed so the labels track the locale and the asset list follows the account. */
const fields = computed<FieldDef[]>(() => toAccountHistoryFields(shared, t, {
  accounts,
  assets: restrictAssets ? (): string[] => assets : undefined,
  locations: restrictAssets ? (): string[] => locations : undefined,
  searchAsset,
}));

/** Written through by the bar into the page's selection, which clears the picks below a changed one. */
const params = accountHistoryParams(account, asset, location);
</script>

<template>
  <div class="flex flex-col gap-1">
    <PillFilterBar
      v-model:params="params"
      :fields="fields"
      :labels="pillLabels"
      data-testid="account-history-filter"
    />
    <div
      v-if="restrictAssets && assetsProcessingRequired"
      class="text-caption text-rui-text-secondary px-1"
      data-testid="account-history-assets-processing"
    >
      {{ t('account_history.selectors.asset_hint_processing') }}
    </div>
  </div>
</template>
