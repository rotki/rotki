<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { isEqual } from 'lodash-es';

const renderAllNftImages: Ref<boolean> = ref(true);
const whitelistedDomainsForNftImages: Ref<string[]> = ref([]);

const frontendStore = useFrontendSettingsStore();
const {
  renderAllNftImages: renderAll,
  whitelistedDomainsForNftImages: whitelist
} = storeToRefs(frontendStore);

const { updateSetting } = frontendStore;

onMounted(() => {
  set(renderAllNftImages, get(renderAll));
  set(whitelistedDomainsForNftImages, get(whitelist));
});

const onChange = (value: string[]) => {
  set(
    whitelistedDomainsForNftImages,
    value.map(val => getDomain(val)).filter(uniqueStrings)
  );
};

const updateWhitelist = () => {
  updateSetting({
    whitelistedDomainsForNftImages: get(whitelistedDomainsForNftImages)
  });
  set(showUpdateWhitelistConfirmation, false);
};

const reset = () => {
  set(whitelistedDomainsForNftImages, get(whitelist));
  set(showUpdateWhitelistConfirmation, false);
};

watch(whitelist, data => {
  set(whitelistedDomainsForNftImages, data);
});

const { t } = useI18n();

const showUpdateWhitelistConfirmation: Ref<boolean> = ref(false);

const changed: ComputedRef<boolean> = computed(
  () => !isEqual(get(whitelistedDomainsForNftImages), get(whitelist))
);

const confirmUpdated = () => {
  const currentValue = get(whitelistedDomainsForNftImages);
  if (currentValue.length === 0 || !get(changed)) {
    updateWhitelist();
    return;
  }
  set(showUpdateWhitelistConfirmation, true);
};

const { show } = useConfirmStore();
const updateRenderingSetting = (
  value: boolean,
  update: (value: any) => void
) => {
  if (!value) {
    update(value);
    return;
  }

  show(
    {
      title: t('general_settings.nft_setting.allow_all_confirmation.title'),
      message: t('general_settings.nft_setting.allow_all_confirmation.message'),
      type: 'info'
    },
    () => {
      update(value);
    },
    () => {
      set(renderAllNftImages, false);
    }
  );
};

const css = useCssModule();

const warningUrl =
  'https://medium.com/@alxlpsc/critical-privacy-vulnerability-getting-exposed-by-metamask-693c63c2ce94';
</script>

<template>
  <div>
    <div>
      <div class="text-h6">
        {{
          t(
            'general_settings.nft_setting.subtitle.nft_images_rendering_setting'
          )
        }}
      </div>
      <i18n
        tag="div"
        class="mt-1"
        path="general_settings.nft_setting.subtitle.nft_images_rendering_setting_hint"
      >
        <template #link>
          <ExternalLink :url="warningUrl">
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n>
    </div>
    <SettingsOption
      #default="{ error, success, update }"
      setting="renderAllNftImages"
      frontend-setting
    >
      <VRadioGroup
        v-model="renderAllNftImages"
        :success-messages="success"
        :error-messages="error"
        @change="updateRenderingSetting($event, update)"
      >
        <VRadio
          :label="
            t('general_settings.nft_setting.label.render_setting.allow_all')
          "
          :value="true"
        />
        <VRadio
          :label="
            t(
              'general_settings.nft_setting.label.render_setting.only_allow_whitelisted'
            )
          "
          :value="false"
        />
      </VRadioGroup>
    </SettingsOption>

    <VRow class="mt-4">
      <VCol>
        <SettingsOption
          setting="whitelistedDomainsForNftImages"
          frontend-setting
        >
          <VCombobox
            v-model="whitelistedDomainsForNftImages"
            :class="css['whitelisted-input']"
            :label="t('general_settings.nft_setting.label.whitelisted_domains')"
            :hint="
              t('general_settings.nft_setting.label.whitelisted_domains_hint')
            "
            persistent-hint
            chips
            outlined
            deletable-chips
            clearable
            multiple
            :disabled="renderAllNftImages"
            @change="onChange($event)"
          />
        </SettingsOption>
      </VCol>
      <VCol cols="auto">
        <VBtn class="mt-2" icon :disabled="!changed" @click="confirmUpdated()">
          <VIcon>mdi-content-save</VIcon>
        </VBtn>
      </VCol>
    </VRow>

    <ConfirmDialog
      :display="showUpdateWhitelistConfirmation"
      :title="
        t('general_settings.nft_setting.update_whitelist_confirmation.title')
      "
      :message="
        t(
          'general_settings.nft_setting.update_whitelist_confirmation.message',
          1
        )
      "
      max-width="700"
      @cancel="reset()"
      @confirm="updateWhitelist()"
    >
      <VSheet outlined class="pa-4 mt-4" rounded>
        <ul>
          <li
            v-for="domain in whitelistedDomainsForNftImages"
            :key="domain"
            class="orange--text font-bold"
          >
            {{ domain }}
          </li>
        </ul>
      </VSheet>
    </ConfirmDialog>
  </div>
</template>

<style module lang="scss">
.whitelisted-input {
  :global {
    .v-select {
      &__selections {
        min-height: auto !important;
      }
    }
  }
}
</style>
