<script setup lang="ts">
const props = defineProps({
  identifier: {
    required: true,
    type: String
  },
  refreshable: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { identifier } = toRefs(props);

const preview = computed<string | null>(() => get(identifier) ?? null);
const icon = ref<File | null>(null);

const refreshIconLoading = ref<boolean>(false);
const timestamp = ref<number | null>(null);
const { notify } = useNotificationsStore();
const { appSession } = useInterop();
const { setMessage } = useMessageStore();
const { refreshIcon: refresh, setIcon, uploadIcon } = useAssetIconApi();

const { t, tc } = useI18n();

const refreshIcon = async () => {
  set(refreshIconLoading, true);
  const identifierVal = get(identifier);
  try {
    await refresh(identifierVal);
  } catch (e: any) {
    notify({
      title: tc('asset_form.fetch_latest_icon.title'),
      message: tc('asset_form.fetch_latest_icon.description', 0, {
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
      title: tc('asset_form.icon_upload.title'),
      description: tc('asset_form.icon_upload.description', 0, {
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
    <v-row>
      <v-col cols="auto">
        <v-sheet outlined rounded class="asset-form__icon">
          <v-tooltip v-if="preview && refreshable" right>
            <template #activator="{ on }">
              <v-btn
                fab
                x-small
                depressed
                class="asset-form__icon__refresh"
                color="primary"
                :loading="refreshIconLoading"
                v-on="on"
                @click="refreshIcon"
              >
                <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </template>
            {{ t('asset_form.fetch_latest_icon.title') }}
          </v-tooltip>

          <asset-icon
            v-if="preview"
            :identifier="preview"
            size="72px"
            changeable
            :timestamp="timestamp"
          />
        </v-sheet>
      </v-col>
      <v-col>
        <file-upload
          source="icon"
          file-filter="image/*"
          @selected="icon = $event"
        />
      </v-col>
    </v-row>
    <v-row v-if="icon">
      <v-col class="text-caption">
        {{ t('asset_form.replaced', { name: icon.name }) }}
      </v-col>
    </v-row>
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
