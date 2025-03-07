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
const { t } = useI18n();

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
      <AssetDetails
        v-if="!isNft(asset)"
        :class="$style.asset"
        :asset="asset"
        :opens-details="false"
        :enable-association="false"
      />
      <div v-else>
        <NftDetails
          :identifier="asset"
          :class="$style.asset"
        />
      </div>
    </div>
  </ConfirmDialog>
</template>

<style module lang="scss">
.asset {
  max-width: 640px;
}
</style>
