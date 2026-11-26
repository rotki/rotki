<script setup lang="ts">
import { RuiButton } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';

const ignoredAssetsHandling = defineModel<IgnoredAssetsHandlingType>('ignoredAssetsHandling', { required: true });

const { t } = useI18n({ useScope: 'global' });

/** Hiding ignored or unignored NFTs can leave an empty table that is only a filter away from rows. */
const filtered = computed<boolean>(() => get(ignoredAssetsHandling) !== IgnoredAssetHandlingType.NONE);

function showAll(): void {
  set(ignoredAssetsHandling, IgnoredAssetHandlingType.NONE);
}
</script>

<template>
  <TableEmptyNotice
    :icon="filtered ? 'lu-search-x' : 'lu-image'"
    :title="filtered ? t('non_fungible_balances.empty.filtered_title') : t('non_fungible_balances.empty.title')"
    :description="filtered ? t('non_fungible_balances.empty.filtered_description') : t('non_fungible_balances.empty.description')"
    :data-testid="filtered ? 'nft-balances-empty-filtered' : 'nft-balances-empty'"
  >
    <RuiButton
      v-if="filtered"
      variant="outlined"
      color="primary"
      data-testid="nft-balances-empty-show-all"
      @click="showAll()"
    >
      {{ t('non_fungible_balances.empty.show_all') }}
    </RuiButton>
  </TableEmptyNotice>
</template>
