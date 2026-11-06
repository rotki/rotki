<script setup lang="ts">
import { map as mapResult, ok, type Result } from 'plainfp/result';
import { fromPromise } from 'plainfp/result-async';
import { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const { identifier, refreshable = false } = defineProps<{
  identifier: string;
  refreshable?: boolean;
}>();

const preview = computed<string | null>(() => identifier ?? null);
const icon = ref<File>();

const refreshIconLoading = ref<boolean>(false);
const refreshKey = ref<number>(0);
/** Why the last icon refresh failed, named under the icon with a retry. */
const refreshError = shallowRef<unknown>();
const { getPath } = useInterop();
const { refreshIcon: refresh, setIcon, uploadIcon } = useAssetIconApi();

const { t } = useI18n({ useScope: 'global' });

const { setLastRefreshedAssetIcon } = useAssetsStore();

async function refreshIcon() {
  if (get(refreshIconLoading))
    return;

  set(refreshIconLoading, true);
  set(refreshError, undefined);
  try {
    await refresh(identifier);
    set(refreshKey, get(refreshKey) + 1);
  }
  catch (error: unknown) {
    set(refreshError, error);
  }
  set(refreshIconLoading, false);
  setLastRefreshedAssetIcon();
}

/**
 * Uploads the chosen icon for an asset that was just saved.
 *
 * @returns `ok` once the icon is stored, or straight away when none was chosen; `err` with the
 * upload's error, for the dialog to name while it stays open
 */
async function saveIcon(identifier: string): Promise<Result<void, unknown>> {
  const iconVal = get(icon);
  if (!iconVal)
    return ok(undefined);

  const path = getPath(iconVal);
  const request = path ? setIcon(identifier, path) : uploadIcon(identifier, iconVal);
  const uploaded = await fromPromise(request, (error: unknown) => error);
  if (uploaded.ok)
    setLastRefreshedAssetIcon();
  return mapResult(uploaded, () => undefined);
}

const previewImageSource = ref<string>('');
watch(icon, (icon) => {
  if (icon && icon.type.startsWith('image')) {
    const reader = new FileReader();
    reader.onload = (e) => {
      set(previewImageSource, e.target?.result || '');
    };
    reader.readAsDataURL(icon);
  }
  else {
    set(previewImageSource, '');
  }
});

defineExpose({
  saveIcon,
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="text-sm font-medium text-rui-text">
      {{ t('asset_form.labels.icon') }}
    </div>
    <div class="grid grid-cols-[auto_1fr] gap-4">
      <div class="relative size-28 flex items-center justify-center rounded-rui-control border border-rui-divider bg-rui-surface">
        <RuiTooltip
          v-if="preview && refreshable"
          :options="{ placement: 'right' }"
          :open-delay="400"
          class="absolute -top-3 -right-3"
        >
          <template #activator>
            <RuiButton
              size="sm"
              icon
              color="primary"
              :loading="refreshIconLoading"
              data-testid="asset-icon-refresh"
              @click="refreshIcon()"
            >
              <RuiIcon
                size="20"
                name="lu-refresh-ccw"
              />
            </RuiButton>
          </template>
          {{ t('asset_form.fetch_latest_icon.title') }}
        </RuiTooltip>

        <AppImage
          v-if="icon && previewImageSource"
          :src="previewImageSource"
          size="4.5rem"
          fit="contain"
        />
        <AssetIcon
          v-else-if="preview"
          :key="refreshKey"
          :identifier="preview"
          size="72px"
          no-tooltip
          :show-chain="false"
        />
        <RuiIcon
          v-else
          name="lu-image"
          size="32"
          class="text-rui-text-disabled"
        />
      </div>
      <RuiFileUpload
        v-model="icon"
        accept=".png,.svg,.jpeg,.jpg,.webp"
        :upload-text="t('file_upload.dropzone.prefix')"
        :click-to-upload-text="t('file_upload.dropzone.choose')"
        :replace-text="t('file_upload.dropzone.replace')"
        :hint="icon && identifier ? t('asset_form.replaced') : undefined"
        details="auto"
        data-testid="asset-icon-upload"
      />
    </div>
    <FailureStrip
      v-if="refreshError"
      :title="t('asset_form.fetch_latest_icon.failed')"
      :failure="refreshError"
      data-testid="asset-icon-refresh-error"
      @retry="refreshIcon()"
    />
  </div>
</template>
