<script setup lang="ts">
import type { BalanceSnapshot } from '@/modules/dashboard/snapshots';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import { isNft } from '@/modules/assets/nft-utils';

const { snapshot } = defineProps<{
  snapshot: BalanceSnapshot | null;
}>();
const emit = defineEmits<{
  cancel: [];
  confirm: [];
}>();
const { t } = useI18n({ useScope: 'global' });

const display = computed<boolean>(() => !!snapshot);

const asset = computed<string>(() => snapshot?.assetIdentifier ?? '');
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
        class="max-w-[640px]"
      />
      <AssetDetails
        v-else
        hide-menu
        class="max-w-[640px]"
        :asset="asset"
        :enable-association="false"
      />
    </div>
  </ConfirmDialog>
</template>
