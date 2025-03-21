<script setup lang="ts">
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useConfirmStore } from '@/store/confirm';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { uniqueStrings } from '@/utils/data';
import { getDomain } from '@/utils/url';
import { isEqual } from 'es-toolkit';

type RenderOption = 'all' | 'whitelisted';

const emit = defineEmits<{ (e: 'dialog-open', value: boolean): void }>();

const { t } = useI18n();

const confirmStore = useConfirmStore();
const frontendStore = useFrontendSettingsStore();
const { visible } = storeToRefs(confirmStore);
const { renderAllNftImages: renderAll, whitelistedDomainsForNftImages: whitelist } = storeToRefs(frontendStore);

const renderAllNftImages = ref<RenderOption>('all');
const whitelistedDomains = ref('');
const showUpdateWhitelistConfirmation = ref(false);

const decodedDomains = computed<string[]>(() =>
  get(whitelistedDomains)
    .split(',')
    .filter(value => !!value)
    .map(val => getDomain(val.trim())),
);

const whitelistedDomainsForNftImages = computed<string[]>(() =>
  [...get(whitelist), ...get(decodedDomains)].filter(uniqueStrings),
);

const changed = computed(() => !isEqual(get(whitelistedDomainsForNftImages), get(whitelist)));

const { show } = confirmStore;

function updateRenderingSetting(value: RenderOption | undefined, update: (value: any) => void) {
  if (value === 'whitelisted') {
    update(false);
    return;
  }

  show(
    {
      message: t('general_settings.nft_setting.allow_all_confirmation.message'),
      title: t('general_settings.nft_setting.allow_all_confirmation.title'),
      type: 'info',
    },
    () => {
      update(value === 'all');
    },
    () => {
      set(renderAllNftImages, 'whitelisted');
    },
  );
}

watch([showUpdateWhitelistConfirmation, visible], ([isSaveOpen, isSwitchOpen]) => {
  emit('dialog-open', isSaveOpen || isSwitchOpen);
});

onMounted(() => {
  set(renderAllNftImages, get(renderAll) ? 'all' : 'whitelisted');
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="renderAllNftImages"
    frontend-setting
  >
    <RuiRadioGroup
      v-model="renderAllNftImages"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateRenderingSetting($event, updateImmediate)"
    >
      <RuiRadio value="all">
        {{ t('general_settings.nft_setting.label.render_setting.allow_all') }}
      </RuiRadio>
      <RuiRadio value="whitelisted">
        {{ t('general_settings.nft_setting.label.render_setting.only_allow_whitelisted') }}
      </RuiRadio>
    </RuiRadioGroup>
  </SettingsOption>

  <SettingsOption
    #default="{ error, success, updateImmediate }"
    :error-message="t('general_settings.nft_setting.messages.error')"
    :success-message="t('general_settings.nft_setting.messages.success')"
    setting="whitelistedDomainsForNftImages"
    frontend-setting
    @updated="whitelistedDomains = ''"
  >
    <div class="flex flex-row gap-3.5 items-start">
      <RuiTextField
        v-model.trim="whitelistedDomains"
        color="primary"
        :label="t('general_settings.nft_setting.label.whitelist_domains')"
        :hint="t('general_settings.nft_setting.label.whitelisted_domains_hint')"
        :success-messages="success"
        :error-messages="error"
        :disabled="renderAllNftImages === 'all'"
        class="flex-1"
        variant="outlined"
        clearable
      />
      <RuiButton
        :disabled="!changed"
        class="mt-1"
        variant="text"
        color="primary"
        icon
        @click="showUpdateWhitelistConfirmation = true"
      >
        <RuiIcon name="lu-save" />
      </RuiButton>
    </div>

    <p class="text-caption text-rui-text mt-1 mb-0 px-3">
      {{ t('general_settings.nft_setting.label.whitelisted_domain_entries', { count: decodedDomains.length }) }}
    </p>

    <template v-if="whitelist.length > 0">
      <h5 class="mt-4 mb-2 font-medium">
        {{ t('general_settings.nft_setting.label.whitelisted_domains') }}
      </h5>

      <div class="flex flex-wrap gap-2">
        <RuiChip
          v-for="(item, i) in whitelist"
          :key="i"
          :disabled="renderAllNftImages !== 'whitelisted'"
          :closeable="renderAllNftImages === 'whitelisted'"
          size="sm"
          @click:close="updateImmediate(whitelist.filter((domain) => domain !== item))"
        >
          {{ item }}
        </RuiChip>
      </div>
    </template>

    <ConfirmDialog
      :display="showUpdateWhitelistConfirmation"
      :title="t('general_settings.nft_setting.update_whitelist_confirmation.title')"
      :message="t('general_settings.nft_setting.update_whitelist_confirmation.message', 1)"
      max-width="700"
      @cancel="showUpdateWhitelistConfirmation = false"
      @confirm="
        updateImmediate(whitelistedDomainsForNftImages);
        showUpdateWhitelistConfirmation = false;
      "
    >
      <RuiCard
        outlined
        class="mt-4 h-auto"
      >
        <ul class="list-disc pl-5">
          <li
            v-for="domain in whitelistedDomainsForNftImages"
            :key="domain"
            class="text-rui-warning font-bold"
          >
            {{ domain }}
          </li>
        </ul>
      </RuiCard>
    </ConfirmDialog>
  </SettingsOption>
</template>
