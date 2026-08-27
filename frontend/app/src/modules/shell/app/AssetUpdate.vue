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
      @check="check()"
    />
    <template v-else-if="headless">
      <AssetUpdateStatus
        v-if="status"
        :status="status"
        :remote-version="modelChanges.upToVersion"
      />
      <AssetUpdateInlineConfirm
        v-if="inlineConfirm"
        class="max-w-[32rem] mx-auto"
        :remote-version="modelChanges.upToVersion"
        @confirm="updateComplete()"
      />
    </template>
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
        class="max-w-[32rem] mx-auto"
        :headless="headless"
        :versions="modelChanges"
        @update:versions="modelChanges = $event"
        @confirm="updateAssets()"
        @dismiss="skip($event)"
      />
    </template>

    <AssetConflictDialog
      v-if="modelShowConflictDialog"
      v-model="modelShowConflictDialog"
      :conflicts="conflicts"
      @cancel="skip(false)"
      @resolve="updateAssets($event)"
    />
  </div>
</template>
