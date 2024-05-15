<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    identifier: string;
    refreshable?: boolean;
  }>(),
  { refreshable: false },
);

const { identifier } = toRefs(props);

const preview = computed<string | null>(() => get(identifier) ?? null);
const icon = ref<File | null>(null);

const refreshIconLoading = ref<boolean>(false);
const { notify } = useNotificationsStore();
const { appSession } = useInterop();
const { setMessage } = useMessageStore();
const { refreshIcon: refresh, setIcon, uploadIcon } = useAssetIconApi();

const { t } = useI18n();

const { setLastRefreshedAssetIcon } = useAssetIconStore();

async function refreshIcon() {
  set(refreshIconLoading, true);
  const identifierVal = get(identifier);
  try {
    await refresh(identifierVal);
  }
  catch (error: any) {
    notify({
      title: t('asset_form.fetch_latest_icon.title'),
      message: t('asset_form.fetch_latest_icon.description', {
        identifier: identifierVal,
        message: error.message,
      }),
      display: true,
    });
  }
  set(refreshIconLoading, false);
  setLastRefreshedAssetIcon();
}

async function saveIcon(identifier: string) {
  const iconVal = get(icon);
  if (!iconVal)
    return;

  try {
    if (appSession)
      await setIcon(identifier, iconVal.path);
    else
      await uploadIcon(identifier, iconVal);

    setLastRefreshedAssetIcon();
  }
  catch (error: any) {
    const message = error.message;

    setMessage({
      title: t('asset_form.icon_upload.title'),
      description: t('asset_form.icon_upload.description', {
        message,
      }),
    });
  }
}

const previewImageSource: Ref<string> = ref('');
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
  <div>
    <div class="grid grid-cols-[auto_1fr] gap-6 h-full">
      <RuiCard
        rounded="sm"
        class="w-32 items-center justify-center [&>div]:!p-6 relative"
      >
        <RuiTooltip
          v-if="preview && refreshable"
          :popper="{ placement: 'right' }"
          :open-delay="400"
          class="absolute -top-3 -right-3"
        >
          <template #activator>
            <RuiButton
              size="sm"
              icon
              color="primary"
              :loading="refreshIconLoading"
              @click="refreshIcon()"
            >
              <RuiIcon
                size="20"
                name="refresh-line"
              />
            </RuiButton>
          </template>
          {{ t('asset_form.fetch_latest_icon.title') }}
        </RuiTooltip>

        <AppImage
          v-if="icon && previewImageSource"
          :src="previewImageSource"
          size="4.5rem"
          contain
        />
        <AssetIcon
          v-else-if="preview"
          :identifier="preview"
          size="72px"
          changeable
          :show-chain="false"
        />
      </RuiCard>
      <FileUpload
        v-model="icon"
        class="grow"
        source="icon"
        file-filter=".png, .svg, .jpeg, .jpg, .webp"
      />
    </div>
    <div
      v-if="icon && identifier"
      class="text-caption text-rui-success mt-2"
    >
      {{ t('asset_form.replaced') }}
    </div>
  </div>
</template>
