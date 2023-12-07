<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { isNft } from '@/utils/nft';
import NftDetails from '@/components/helper/NftDetails.vue';
import { type BalanceSnapshot } from '@/types/snapshots';

const props = defineProps<{
  snapshot: BalanceSnapshot | null;
}>();
const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'confirm'): void;
}>();
const { t } = useI18n();
const css = useCssModule();

const { snapshot } = toRefs(props);

const display: ComputedRef<boolean> = computed(() => !!get(snapshot));

const asset: ComputedRef<string> = computed(
  () => get(snapshot)?.assetIdentifier ?? ''
);
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
    <div
      class="flex justify-center align-center gap-4 mt-4 border border-default rounded px-4"
    >
      <BalanceDisplay :asset="asset" :value="snapshot" class="mr-4" no-icon />
      <AssetDetails
        v-if="!isNft(asset)"
        :class="css.asset"
        :asset="asset"
        :opens-details="false"
        :enable-association="false"
      />
      <div v-else>
        <NftDetails :identifier="asset" :class="css.asset" />
      </div>
    </div>
  </ConfirmDialog>
</template>

<style module lang="scss">
.asset {
  max-width: 640px;
}
</style>
