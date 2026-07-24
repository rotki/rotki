<script setup lang="ts">
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { startPromise } from '@shared/utils';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useSetting } from '@/modules/settings/use-setting';

const open = defineModel<boolean>('open', { required: true });

const { identifiers } = defineProps<{
  identifiers: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const activeAsset = ref<string>();

const currencySymbol = useSetting('currencySymbol');

const { refreshPrice } = usePriceRefresh();

const formOpen = computed<boolean>({
  get: () => isDefined(activeAsset),
  set: (value) => {
    if (!value)
      set(activeAsset, undefined);
  },
});

const prefill = computed<ManualPriceFormPayload | undefined>(() => {
  const asset = get(activeAsset);
  if (!asset)
    return undefined;

  return {
    fromAsset: asset,
    price: '',
    toAsset: get(currencySymbol),
  };
});

function addPrice(asset: string): void {
  set(activeAsset, asset);
}

async function onAdded(asset: string): Promise<void> {
  // Close the form and re-price just the asset we resolved; once it reports a
  // price it drops off the list on its own.
  set(activeAsset, undefined);
  await refreshPrice(asset);
}
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="600"
  >
    <RuiCard>
      <template #header>
        {{ t('dashboard.completeness.missing_prices_dialog.title') }}
      </template>

      <div class="text-body-2 text-rui-text-secondary mb-4">
        {{ t('dashboard.completeness.missing_prices_dialog.description') }}
      </div>

      <div
        v-if="identifiers.length > 0"
        class="border border-rui-grey-300 dark:border-rui-grey-800 rounded overflow-hidden divide-y divide-rui-grey-200 dark:divide-rui-grey-800 max-h-[22.5rem] overflow-y-auto"
        data-testid="missing-prices-list"
      >
        <div
          v-for="asset in identifiers"
          :key="asset"
          class="flex items-center justify-between gap-4 px-4 py-2"
        >
          <AssetDetails
            :asset="asset"
            dense
            hide-menu
            class="min-w-0 max-w-[17.5rem]"
          />
          <RuiButton
            size="sm"
            color="primary"
            variant="outlined"
            class="shrink-0"
            data-testid="missing-price-add"
            @click="addPrice(asset)"
          >
            <template #prepend>
              <RuiIcon
                name="lu-plus"
                size="16"
              />
            </template>
            {{ t('dashboard.completeness.missing_prices_dialog.add_price') }}
          </RuiButton>
        </div>
      </div>

      <div
        v-else
        class="flex flex-col items-center gap-2 py-8 text-rui-text-secondary"
        data-testid="missing-prices-empty"
      >
        <RuiIcon
          name="lu-circle-check"
          size="32"
          class="text-rui-success"
        />
        {{ t('dashboard.completeness.missing_prices_dialog.empty') }}
      </div>

      <template #footer>
        <RouterLink
          class="no-underline"
          :to="{ name: '/price-manager/latest/' }"
        >
          <RuiButton
            variant="text"
            color="primary"
            @click="open = false"
          >
            <template #prepend>
              <RuiIcon
                name="lu-external-link"
                size="16"
              />
            </template>
            {{ t('dashboard.completeness.missing_prices_dialog.open_manager') }}
          </RuiButton>
        </RouterLink>
        <div class="grow" />
        <RuiButton
          color="primary"
          @click="open = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>

    <LatestPriceFormDialog
      v-if="activeAsset"
      :key="activeAsset"
      v-model:open="formOpen"
      :prefill="prefill"
      disable-from-asset
      @refresh="startPromise(onAdded(activeAsset))"
    />
  </RuiDialog>
</template>
