<script setup lang="ts">
import { isMetaMaskSupported } from '@/utils/metamask';
import { externalLinks } from '@/data/external-links';

defineProps<{
  disabled: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:addresses', addresses: string[]): void;
}>();

const { metamaskDownload } = externalLinks;

async function copyPageUrl() {
  const pageUrl = window.location.href;
  const { copy } = useClipboard({ source: pageUrl });
  await copy();
}

const { t } = useI18n();
const [DefineButton, ReuseButton] = createReusableTemplate<{ buttonDisabled: boolean }>();

const { isPackaged, metamaskImport } = useInterop();

async function importAddresses() {
  const addresses = await (isPackaged ? metamaskImport() : getMetamaskAddresses());
  emit('update:addresses', addresses);
}
</script>

<template>
  <DefineButton #default="{ buttonDisabled }">
    <RuiButton
      variant="outlined"
      color="primary"
      class="min-h-[3.5rem]"
      :disabled="buttonDisabled || disabled"
      @click="importAddresses()"
    >
      <template #prepend>
        <AppImage
          contain
          max-width="24px"
          src="./assets/images/metamask-fox.svg"
        />
      </template>
    </RuiButton>
  </DefineButton>
  <div
    v-if="!isPackaged && !isMetaMaskSupported()"
    class="text-rui-warning flex items-center"
  >
    <RuiMenu
      open-on-hover
      :close-delay="4000"
      menu-class="max-w-[20rem]"
      :popper="{ placement: 'right-start' }"
    >
      <template #activator="{ attrs }">
        <ReuseButton
          button-disabled
          v-bind="attrs"
        />
      </template>
      <div class="px-4 py-3">
        <div class="font-bold mb-2">
          {{ t('input_mode_select.metamask_import.missing') }}
          {{ t('input_mode_select.metamask_import.missing_tooltip.title') }}
        </div>
        <ol class="list-disc pl-3">
          <li>
            <i18n-t
              keypath="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_installed"
              tag="span"
            >
              <template #link>
                <ExternalLink
                  :url="metamaskDownload"
                  color="primary"
                >
                  {{ t('common.here') }}
                </ExternalLink>
              </template>
            </i18n-t>
          </li>
          <li>
            {{
              t(
                'input_mode_select.metamask_import.missing_tooltip.metamask_is_not_enabled',
              )
            }}
          </li>
          <li>
            <i18n-t
              keypath="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_supported_by_browser"
              tag="span"
            >
              <template #link>
                <ExternalLink
                  :url="metamaskDownload"
                  color="primary"
                >
                  {{ t('common.here') }}
                </ExternalLink>
              </template>

              <template #copy>
                <RuiButton
                  variant="text"
                  color="primary"
                  class="inline-flex text-[1em] !p-0 !px-1 -mx-1 leading-4"
                  @click="copyPageUrl()"
                >
                  {{
                    t(
                      'input_mode_select.metamask_import.missing_tooltip.copy_url',
                    )
                  }}
                </RuiButton>
              </template>
            </i18n-t>
          </li>
        </ol>
      </div>
    </RuiMenu>
  </div>
  <RuiTooltip
    v-else
    :disabled="disabled"
  >
    <template #activator>
      <ReuseButton :button-disabled="false" />
    </template>
    {{ t('input_mode_select.metamask_import.label') }}
  </RuiTooltip>
</template>
