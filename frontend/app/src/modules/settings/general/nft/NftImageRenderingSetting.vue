<script setup lang="ts">
import {
  hasWhitelistChanges,
  mergeWhitelist,
  parseWhitelistInput,
} from '@/modules/settings/general/nft/nft-whitelist';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

type RenderOption = 'all' | 'whitelisted';

const { t } = useI18n({ useScope: 'global' });

const { error: renderWriteError, model: renderAllModel, success: renderWriteSuccess } = useSettingModel('renderAllNftImages', { debounce: 0 });
const { error: whitelistWriteError, model: whitelistModel, success: whitelistWriteSuccess } = useSettingModel('whitelistedDomainsForNftImages', { debounce: 0 });
const { clearAll: clearRenderMessages, error: renderError, setError: setRenderError, setSuccess: setRenderSuccess, success: renderSuccess } = useClearableMessages();
const { error: whitelistError, success: whitelistSuccess, setError: setWhitelistError, setSuccess: setWhitelistSuccess } = useClearableMessages();

const renderAllNftImages = ref<RenderOption>(get(renderAllModel) ? 'all' : 'whitelisted');
const whitelistedDomains = ref<string>('');
/** Allowing every domain waits on an inline confirmation; the radio shows the pick meanwhile. */
const confirmingAllowAll = ref<boolean>(false);
/** Adding domains waits on an inline confirmation that lists them. */
const confirmingDomains = ref<boolean>(false);

const decodedDomains = computed<string[]>(() => parseWhitelistInput(get(whitelistedDomains)));

const whitelistedDomainsForNftImages = computed<string[]>(() =>
  mergeWhitelist(get(whitelistModel), get(decodedDomains)),
);

/** What the confirmation names: only the domains that are not on the list already. */
const domainsToAdd = computed<string[]>(() => {
  const saved = get(whitelistModel);
  return get(whitelistedDomainsForNftImages).filter(domain => !saved.includes(domain));
});

const changed = computed<boolean>(() =>
  hasWhitelistChanges(get(whitelistModel), get(whitelistedDomainsForNftImages)),
);

function updateRenderingSetting(value: RenderOption | undefined): void {
  clearRenderMessages();
  if (value === 'whitelisted') {
    set(confirmingAllowAll, false);
    set(renderAllModel, false);
    return;
  }
  set(confirmingAllowAll, true);
}

function confirmAllowAll(): void {
  set(confirmingAllowAll, false);
  set(renderAllModel, true);
}

/** Leaving the radio on `all` after a refusal would misreport what is persisted. */
function cancelAllowAll(): void {
  set(confirmingAllowAll, false);
  set(renderAllNftImages, 'whitelisted');
}

function requestDomainsAdd(): void {
  if (get(changed))
    set(confirmingDomains, true);
}

watch(renderAllModel, (value) => {
  if (!get(confirmingAllowAll))
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
  set(confirmingDomains, false);
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

// typing again replaces what was being confirmed
watch(whitelistedDomains, () => {
  set(confirmingDomains, false);
});
</script>

<template>
  <div>
    <RuiRadioGroup
      v-model="renderAllNftImages"
      color="primary"
      :success-messages="renderSuccess"
      :error-messages="renderError"
      data-testid="nft-render-mode"
      @update:model-value="updateRenderingSetting($event)"
    >
      <RuiRadio value="all">
        {{ t('general_settings.nft_setting.label.render_setting.allow_all') }}
      </RuiRadio>
      <RuiRadio value="whitelisted">
        {{ t('general_settings.nft_setting.label.render_setting.only_allow_whitelisted') }}
      </RuiRadio>
    </RuiRadioGroup>

    <div
      v-if="confirmingAllowAll"
      role="alert"
      class="mt-2 rounded-rui-panel border border-rui-warning-border bg-rui-warning-subtle p-3 flex flex-col gap-2"
      data-testid="nft-allow-all-confirmation"
    >
      <p class="text-body-2 m-0">
        {{ t('general_settings.nft_setting.allow_all_confirmation.message') }}
      </p>
      <div class="flex gap-2">
        <RuiButton
          size="sm"
          color="warning"
          data-testid="nft-allow-all-confirm"
          @click="confirmAllowAll()"
        >
          {{ t('general_settings.nft_setting.allow_all_confirmation.confirm') }}
        </RuiButton>
        <RuiButton
          size="sm"
          variant="text"
          data-testid="nft-allow-all-cancel"
          @click="cancelAllowAll()"
        >
          {{ t('general_settings.nft_setting.allow_all_confirmation.cancel') }}
        </RuiButton>
      </div>
    </div>
  </div>

  <div
    v-if="renderAllNftImages === 'whitelisted'"
    class="mt-2"
    data-testid="nft-whitelist"
  >
    <div class="flex gap-2 items-start">
      <RuiTextField
        v-model.trim="whitelistedDomains"
        color="primary"
        :label="t('general_settings.nft_setting.label.whitelist_domains')"
        :placeholder="t('general_settings.nft_setting.label.whitelist_domains_placeholder')"
        :hint="t('general_settings.nft_setting.label.whitelisted_domains_hint')"
        :success-messages="whitelistSuccess"
        :error-messages="whitelistError"
        class="flex-1"
        clearable
        data-testid="nft-whitelist-input"
        @keydown.enter="requestDomainsAdd()"
      />
      <RuiButton
        :disabled="!changed || confirmingDomains"
        class="mt-6"
        variant="outlined"
        color="primary"
        data-testid="nft-whitelist-save"
        @click="requestDomainsAdd()"
      >
        {{ t('general_settings.nft_setting.add') }}
      </RuiButton>
    </div>

    <div
      v-if="confirmingDomains"
      class="mt-2 rounded-rui-panel border border-rui-warning-border bg-rui-warning-subtle p-3 flex flex-col gap-2"
      data-testid="nft-whitelist-confirmation"
    >
      <p class="text-body-2 m-0">
        {{ t('general_settings.nft_setting.update_whitelist_confirmation.message', 1) }}
      </p>
      <div class="flex flex-wrap gap-1">
        <RuiChip
          v-for="domain in domainsToAdd"
          :key="domain"
          size="sm"
          color="warning"
          variant="tonal"
        >
          {{ domain }}
        </RuiChip>
      </div>
      <div class="flex gap-2">
        <RuiButton
          size="sm"
          color="primary"
          data-testid="nft-whitelist-confirm"
          @click="confirmWhitelistUpdate()"
        >
          {{ t('general_settings.nft_setting.update_whitelist_confirmation.confirm') }}
        </RuiButton>
        <RuiButton
          size="sm"
          variant="text"
          data-testid="nft-whitelist-cancel"
          @click="confirmingDomains = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
      </div>
    </div>

    <div
      v-if="whitelistModel.length > 0"
      class="mt-2"
    >
      <h5 class="text-caption text-rui-text-secondary mb-2">
        {{ t('general_settings.nft_setting.label.whitelisted_domains') }}
      </h5>
      <div class="flex flex-wrap gap-2">
        <RuiChip
          v-for="(item, i) in whitelistModel"
          :key="i"
          closeable
          size="sm"
          @click:close="removeDomain(item)"
        >
          {{ item }}
        </RuiChip>
      </div>
    </div>
    <p
      v-else
      class="text-caption text-rui-text-secondary m-0 mt-2"
      data-testid="nft-whitelist-empty"
    >
      {{ t('general_settings.nft_setting.label.whitelist_empty') }}
    </p>
  </div>
</template>
