<script setup lang="ts">
import type { Nullable, SupportedAsset } from '@rotki/common';
import type { Filters } from '@/modules/assets/admin/managed/use-assets-filter';
import { isEqual, keyBy } from 'es-toolkit';
import ManagedAssetFormDialog from '@/modules/assets/admin/managed/ManagedAssetFormDialog.vue';
import ManagedAssetTable from '@/modules/assets/admin/managed/ManagedAssetTable.vue';
import { useManagedAssetFields } from '@/modules/assets/admin/managed/use-managed-asset-fields';
import MergeDialog from '@/modules/assets/admin/MergeDialog.vue';
import RestoreAssetDbButton from '@/modules/assets/admin/RestoreAssetDbButton.vue';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { type AssetRequestPayload, EVM_TOKEN, IgnoredAssetHandlingType, type IgnoredAssetsHandlingType, isIgnoredAssetsHandling } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { identifier = null, mainPage = false } = defineProps<{
  identifier?: string | null;
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const mergeTool = ref<boolean>(false);
const ignoredFilter = ref<{
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>({
  ignoredAssetsHandling: IgnoredAssetHandlingType.EXCLUDE,
  onlyShowOwned: false,
  onlyShowWhitelisted: false,
});

const modelValue = ref<SupportedAsset>();
const editMode = ref<boolean>(false);
const assetTypes = ref<string[]>([]);
const openAction = ref<boolean>(false);

const { expanded, selected } = useCommonTableProps<SupportedAsset>();

const extraParams = computed(() => {
  const { ignoredAssetsHandling, onlyShowOwned, onlyShowWhitelisted } = get(ignoredFilter);
  return {
    ignoredAssetsHandling,
    showUserOwnedAssetsOnly: onlyShowOwned.toString(),
    showWhitelistedAssetsOnly: onlyShowWhitelisted.toString(),
  };
});

const router = useRouter();
const route = useRoute();
const { deleteAsset, queryAllAssets } = useAssetManagementApi();
const { setMessage } = useMessageStore();
const { ignoredAssets } = storeToRefs(useAssetsStore());
const { getAssetTypes } = useAssetManagementApi();

const { deleteCacheKey } = useAssetInfoCache();

const fields = useManagedAssetFields(assetTypes, () => get(ignoredAssets).length);

const {
  collection: assets,
  filter,
  isLoading: loading,
  pagination,
  refetch,
  setPage,
  sort,
} = useServerTable<
  SupportedAsset,
  AssetRequestPayload,
  Filters
>({
  fetch: queryAllAssets,
  fields,
  params: [{
    fromQuery(query): void {
      // A url is anyone's to write, and the handling reaches both the request and the ignored
      // pill's label. An unrecognised one would be sent on while the pill claimed something else,
      // so it falls back to the default rather than being trusted.
      const handling = query.ignoredAssetsHandling;
      set(ignoredFilter, {
        ignoredAssetsHandling: typeof handling === 'string' && isIgnoredAssetsHandling(handling)
          ? handling
          : IgnoredAssetHandlingType.EXCLUDE,
        onlyShowOwned: query.showUserOwnedAssetsOnly === 'true',
        onlyShowWhitelisted: query.showWhitelistedAssetsOnly === 'true',
      });
    },
    to: 'both',
    values: extraParams,
  }],
  sort: {
    default: {
      column: 'symbol',
      direction: 'asc',
    },
  },
  urlState: routeWhen(mainPage),
});

function add() {
  set(modelValue, {
    active: true,
    address: '',
    assetType: EVM_TOKEN,
    customAssetType: '',
    decimals: null,
    ended: null,
    forked: null,
    identifier: '',
    isRebasing: false,
    protocol: '',
    underlyingTokens: null,
  });
  set(editMode, false);
}

function edit(editAsset: SupportedAsset): void {
  set(modelValue, editAsset);
  set(editMode, true);
}

async function editAsset(assetId: Nullable<string>): Promise<void> {
  if (assetId) {
    const all = await queryAllAssets({
      identifiers: [assetId],
      limit: 1,
      offset: 0,
    });

    const foundAsset = all.data[0];
    if (foundAsset)
      edit(foundAsset);
  }
}

const { showDeleteConfirmation } = useTableRowDeletion<SupportedAsset>({
  confirm: item => ({
    message: t('asset_management.confirm_delete.message', { asset: item?.symbol ?? '' }),
    title: t('asset_management.confirm_delete.title'),
  }),
  deleteItem: item => deleteAsset(item.identifier),
  errorMessage: (item, error) => t('asset_management.delete_error', {
    address: item.identifier,
    message: getErrorMessage(error),
  }),
  onDeleted: async (item) => {
    await refetch();
    deleteCacheKey(item.identifier);
  },
});

const assetsMap = computed(() => keyBy(get(assets).data, item => item.identifier));

const selectedRows = computed({
  get() {
    return get(selected).map(({ identifier }) => identifier);
  },
  set(identifiers: string[]) {
    set(
      selected,
      identifiers.map(identifier => get(assetsMap)[identifier]),
    );
  },
});

onMounted(async () => {
  await refetch();
  const query = get(route).query;

  if (identifier || query.add) {
    if (identifier)
      await editAsset(identifier);
    else add();

    await router.replace({ query: {} });
  }
});

watch(() => identifier, async (assetId) => {
  await editAsset(assetId);
});

watch(ignoredFilter, (oldValue, newValue) => {
  if (!isEqual(oldValue, newValue))
    setPage(1);
});

onBeforeMount(async () => {
  try {
    set(assetTypes, await getAssetTypes());
  }
  catch (error: unknown) {
    setMessage({
      description: t('asset_form.types.error', {
        message: getErrorMessage(error),
      }),
    });
  }
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.assets')]">
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        size="lg"
        :loading="loading"
        @click="refetch()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton
        data-testid="managed-asset-add-btn"
        color="primary"
        size="lg"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('managed_asset_content.add_asset') }}
      </RuiButton>
      <RuiMenu
        v-model="openAction"
        :popper="{ placement: 'bottom-end' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="lg"
            v-bind="attrs"
          >
            <RuiIcon name="lu-ellipsis-vertical" />
          </RuiButton>
        </template>
        <RestoreAssetDbButton dropdown />
        <RuiTooltip
          :open-delay="400"
          class="w-full"
          :popper="{ placement: 'left' }"
          tooltip-class="max-w-[200px]"
        >
          <template #activator>
            <RuiButton
              variant="list"
              @click="mergeTool = true; openAction = false"
            >
              <template #prepend>
                <RuiIcon name="lu-combine" />
              </template>
              {{ t('asset_management.merge_assets') }}
            </RuiButton>
          </template>
          {{ t('asset_management.merge_assets_tooltip') }}
        </RuiTooltip>
      </RuiMenu>
    </template>

    <RuiCard>
      <MergeDialog v-model="mergeTool" />

      <ManagedAssetTable
        v-model:filters="filter"
        v-model:ignored-filter="ignoredFilter"
        v-model:expanded="expanded"
        v-model:selected="selectedRows"
        v-model:pagination="pagination"
        v-model:sort="sort"
        :collection="assets"
        :loading="loading"
        :change="!loading"
        :fields="fields"
        @refresh="refetch()"
        @edit="edit($event)"
        @delete-asset="showDeleteConfirmation($event)"
        @update:page="setPage($event)"
      />

      <ManagedAssetFormDialog
        v-model="modelValue"
        :asset-types="assetTypes"
        :edit-mode="editMode"
        @refresh="refetch()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
