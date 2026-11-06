<script setup lang="ts">
import AssetConflictDialog from '@/modules/shell/app/AssetConflictDialog.vue';
import AssetUpdateInlineConfirm from '@/modules/shell/app/AssetUpdateInlineConfirm.vue';
import AssetUpdateMessage from '@/modules/shell/app/AssetUpdateMessage.vue';
import AssetUpdateSetting from '@/modules/shell/app/AssetUpdateSetting.vue';
import AssetUpdateStatus from '@/modules/shell/app/AssetUpdateStatus.vue';
import { useAssetUpdate } from '@/modules/shell/app/use-asset-update';

const { headless = false } = defineProps<{ headless?: boolean }>();

const emit = defineEmits<{
  skip: [];
}>();

const {
  applying,
  check,
  checking,
  conflicts,
  inlineConfirm,
  modelChanges,
  modelShowConflictDialog,
  showUpdateDialog,
  skip,
  skipped,
  status,
  updateAssets,
  updateComplete,
  upToDate,
} = useAssetUpdate({
  headless: () => headless,
  onSkip: () => emit('skip'),
});
</script>

<template>
  <div>
    <AssetUpdateSetting
      v-if="!headless"
      :loading="checking || applying"
      :skipped="skipped"
      :up-to-date="upToDate"
      @check="check()"
    />
    <AssetUpdateStatus
      v-else-if="status"
      :status="status"
      :remote-version="modelChanges.upToVersion"
    />
    <AssetUpdateInlineConfirm
      v-if="inlineConfirm"
      :class="headless ? 'max-w-128 mx-auto' : 'mt-4'"
      :remote-version="modelChanges.upToVersion"
      @confirm="updateComplete()"
    />
    <template v-if="showUpdateDialog">
      <RuiDialog
        v-if="!headless"
        model-value
        max-width="500"
        persistent
      >
        <AssetUpdateMessage
          :headless="headless"
          :versions="modelChanges"
          @update:versions="modelChanges = $event"
          @confirm="updateAssets()"
          @dismiss="skip($event)"
        />
      </RuiDialog>
      <AssetUpdateMessage
        v-else
        class="max-w-128 mx-auto"
        :headless="headless"
        :versions="modelChanges"
        @update:versions="modelChanges = $event"
        @confirm="updateAssets()"
        @dismiss="skip($event)"
      />
    </template>

    <AssetConflictDialog
      v-if="modelShowConflictDialog"
      :conflicts="conflicts"
      @cancel="skip(false)"
      @resolve="updateAssets($event)"
    />
  </div>
</template>
