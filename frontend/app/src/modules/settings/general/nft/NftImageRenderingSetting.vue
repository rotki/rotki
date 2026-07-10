<script setup lang="ts">
import { isEqual } from 'es-toolkit';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { getDomain } from '@/modules/core/common/helpers/url';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

type RenderOption = 'all' | 'whitelisted';

const emit = defineEmits<{ 'dialog-open': [value: boolean] }>();

const { t } = useI18n({ useScope: 'global' });

const confirmStore = useConfirmStore();
const { visible } = storeToRefs(confirmStore);
const { show } = confirmStore;

const { error: renderWriteError, model: renderAllModel, success: renderWriteSuccess } = useSettingModel('renderAllNftImages', { debounce: 0 });
const { error: whitelistWriteError, model: whitelistModel, success: whitelistWriteSuccess } = useSettingModel('whitelistedDomainsForNftImages', { debounce: 0 });
const { clearAll: clearRenderMessages, error: renderError, setError: setRenderError, setSuccess: setRenderSuccess, success: renderSuccess } = useClearableMessages();
const { error: whitelistError, success: whitelistSuccess, setError: setWhitelistError, setSuccess: setWhitelistSuccess } = useClearableMessages();

const renderAllNftImages = ref<RenderOption>(get(renderAllModel) ? 'all' : 'whitelisted');
const whitelistedDomains = ref('');
const showUpdateWhitelistConfirmation = ref(false);

const decodedDomains = computed<string[]>(() =>
  get(whitelistedDomains)
    .split(',')
    .filter(value => !!value)
    .map(val => getDomain(val.trim())),
);

const whitelistedDomainsForNftImages = computed<string[]>(() =>
  [...get(whitelistModel), ...get(decodedDomains)].filter(uniqueStrings),
);

const changed = computed(() => !isEqual(get(whitelistedDomainsForNftImages), get(whitelistModel)));

function updateRenderingSetting(value: RenderOption | undefined): void {
  clearRenderMessages();
  if (value === 'whitelisted') {
    set(renderAllModel, false);
    return;
  }

  show(
    {
      message: t('general_settings.nft_setting.allow_all_confirmation.message'),
      title: t('general_settings.nft_setting.allow_all_confirmation.title'),
      type: 'info',
    },
    () => {
      set(renderAllModel, value === 'all');
    },
    () => {
      set(renderAllNftImages, 'whitelisted');
    },
  );
}

watch([showUpdateWhitelistConfirmation, visible], ([isSaveOpen, isSwitchOpen]) => {
  emit('dialog-open', isSaveOpen || isSwitchOpen);
});

watch(renderAllModel, (value) => {
  set(renderAllNftImages, value ? 'all' : 'whitelisted');
});

watch(renderWriteSuccess, (saved) => {
  if (saved)
    setRenderSuccess('', true);
});

watch(renderWriteError, (message) => {
  if (message)
    setRenderError(message, true);
});

function removeDomain(item: string): void {
  set(whitelistModel, get(whitelistModel).filter(domain => domain !== item));
}

function confirmWhitelistUpdate(): void {
  set(whitelistModel, get(whitelistedDomainsForNftImages));
  set(showUpdateWhitelistConfirmation, false);
}

watch(whitelistWriteSuccess, (saved) => {
  if (saved) {
    setWhitelistSuccess(t('general_settings.nft_setting.messages.success'), true);
    set(whitelistedDomains, '');
  }
});

watch(whitelistWriteError, (message) => {
  if (message)
    setWhitelistError(`${t('general_settings.nft_setting.messages.error')}: ${message}`, true);
});
</script>

<template>
  <div>
    <RuiRadioGroup
      v-model="renderAllNftImages"
      color="primary"
      :success-messages="renderSuccess"
      :error-messages="renderError"
      @update:model-value="updateRenderingSetting($event)"
    >
      <RuiRadio value="all">
        {{ t('general_settings.nft_setting.label.render_setting.allow_all') }}
      </RuiRadio>
      <RuiRadio value="whitelisted">
        {{ t('general_settings.nft_setting.label.render_setting.only_allow_whitelisted') }}
      </RuiRadio>
    </RuiRadioGroup>
  </div>

  <div>
    <div class="flex flex-row gap-3.5 items-start">
      <RuiTextField
        v-model.trim="whitelistedDomains"
        color="primary"
        :label="t('general_settings.nft_setting.label.whitelist_domains')"
        :hint="t('general_settings.nft_setting.label.whitelisted_domains_hint')"
        :success-messages="whitelistSuccess"
        :error-messages="whitelistError"
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

    <template v-if="whitelistModel.length > 0">
      <h5 class="mt-4 mb-2 font-medium">
        {{ t('general_settings.nft_setting.label.whitelisted_domains') }}
      </h5>

      <div class="flex flex-wrap gap-2">
        <RuiChip
          v-for="(item, i) in whitelistModel"
          :key="i"
          :disabled="renderAllNftImages !== 'whitelisted'"
          :closeable="renderAllNftImages === 'whitelisted'"
          size="sm"
          @click:close="removeDomain(item)"
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
      @confirm="confirmWhitelistUpdate()"
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
  </div>
</template>
