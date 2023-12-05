<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    identifier: string;
    refreshable?: boolean;
  }>(),
  { refreshable: false }
);

const { identifier } = toRefs(props);

const preview = computed<string | null>(() => get(identifier) ?? null);
const icon = ref<File | null>(null);

const refreshIconLoading = ref<boolean>(false);
const timestamp = ref<number | null>(null);
const { notify } = useNotificationsStore();
const { appSession } = useInterop();
const { setMessage } = useMessageStore();
const { refreshIcon: refresh, setIcon, uploadIcon } = useAssetIconApi();

const { t } = useI18n();

const refreshIcon = async () => {
  set(refreshIconLoading, true);
  const identifierVal = get(identifier);
  try {
    await refresh(identifierVal);
  } catch (e: any) {
    notify({
      title: t('asset_form.fetch_latest_icon.title'),
      message: t('asset_form.fetch_latest_icon.description', {
        identifier: identifierVal,
        message: e.message
      }),
      display: true
    });
  }
  set(refreshIconLoading, false);
  set(timestamp, Date.now());
};

const saveIcon = async (identifier: string) => {
  if (!get(icon)) {
    return;
  }

  let success = false;
  let message = '';
  try {
    if (appSession) {
      await setIcon(identifier, get(icon)!.path);
    } else {
      await uploadIcon(identifier, get(icon)!);
    }
    success = true;
  } catch (e: any) {
    message = e.message;
  }

  if (!success) {
    setMessage({
      title: t('asset_form.icon_upload.title'),
      description: t('asset_form.icon_upload.description', {
        message
      })
    });
  }
};

defineExpose({
  saveIcon
});
</script>

<template>
  <div>
    <div class="flex gap-6">
      <div>
        <RuiCard
          class="h-full flex items-center justify-center relative [&>div]:!p-6"
        >
          <RuiTooltip
            v-if="preview && refreshable"
            :popper="{ placement: 'right' }"
            open-delay="400"
            class="absolute top-0 right-0"
          >
            <template #activator="{ on }">
              <RuiButton
                size="sm"
                icon
                color="primary"
                :loading="refreshIconLoading"
                v-on="on"
                @click="refreshIcon()"
              >
                <RuiIcon size="20" name="refresh-line" />
              </RuiButton>
            </template>
            {{ t('asset_form.fetch_latest_icon.title') }}
          </RuiTooltip>

          <AssetIcon
            v-if="preview"
            :identifier="preview"
            size="72px"
            changeable
            :timestamp="timestamp"
          />
        </RuiCard>
      </div>
      <FileUpload
        v-model="icon"
        class="grow"
        source="icon"
        file-filter=".png, .svg, .jpeg, .jpg, .webp"
      />
    </div>
    <div v-if="icon" class="text-caption text-rui-success mt-2">
      {{ t('asset_form.replaced', { name: icon.name }) }}
    </div>
  </div>
</template>
