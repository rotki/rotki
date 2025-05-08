<script setup lang="ts">
import type { BalanceSnapshot } from '@/types/snapshots';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import { isNft } from '@/utils/nft';

const props = defineProps<{
  snapshot: BalanceSnapshot | null;
}>();
const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'confirm'): void;
}>();
const { t } = useI18n({ useScope: 'global' });

const { snapshot } = toRefs(props);

const display = computed<boolean>(() => !!get(snapshot));

const asset = computed<string>(() => get(snapshot)?.assetIdentifier ?? '');
</script>

<template>
  <ConfirmDialog
    max-width="700"
    :display="display"
    :title="t('dashboard.snapshot.convert_to_edit.dialog.title')"
    :message="t('dashboard.snapshot.convert_to_edit.dialog.subtitle')"
    :primary-action="t('dashboard.snapshot.convert_to_edit.dialog.actions.yes')"
    @cancel="emit('cancel')"
    @confirm="emit('confirm')"
  >
    <div class="flex justify-center items-center gap-4 mt-4 border border-default rounded px-4">
      <BalanceDisplay
        :asset="asset"
        :value="snapshot"
        class="mr-4"
        no-icon
      />

      <NftDetails
        v-if="isNft(asset)"
        :identifier="asset"
        :class="$style.asset"
      />
      <AssetDetails
        v-else
        hide-menu
        :class="$style.asset"
        :asset="asset"
        :enable-association="false"
      />
    </div>
  </ConfirmDialog>
</template>

<style module lang="scss">
.asset {
  max-width: 640px;
}
</style>
