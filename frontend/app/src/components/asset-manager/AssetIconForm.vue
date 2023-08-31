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
    <VRow>
      <VCol cols="auto">
        <VSheet outlined rounded class="asset-form__icon">
          <VTooltip v-if="preview && refreshable" right>
            <template #activator="{ on }">
              <VBtn
                fab
                x-small
                depressed
                class="asset-form__icon__refresh"
                color="primary"
                :loading="refreshIconLoading"
                v-on="on"
                @click="refreshIcon()"
              >
                <RuiIcon name="refresh-line" />
              </VBtn>
            </template>
            {{ t('asset_form.fetch_latest_icon.title') }}
          </VTooltip>

          <AssetIcon
            v-if="preview"
            :identifier="preview"
            size="72px"
            changeable
            :timestamp="timestamp"
          />
        </VSheet>
      </VCol>
      <VCol>
        <FileUpload
          source="icon"
          file-filter=".png, .svg, .jpeg, .jpg, .webp"
          @selected="icon = $event"
        />
      </VCol>
    </VRow>
    <VRow v-if="icon">
      <VCol class="text-caption">
        {{ t('asset_form.replaced', { name: icon.name }) }}
      </VCol>
    </VRow>
  </div>
</template>

<style scoped lang="scss">
.asset-form {
  &__icon {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    width: 96px;
    height: 100%;
    position: relative;

    &__refresh {
      position: absolute;
      right: -1rem;
      top: -1rem;
    }
  }
}
</style>
