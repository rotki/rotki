<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { isBtcChain } from '@/types/blockchain/chains';
import { InputMode } from '@/types/input-mode';
import { isMetaMaskSupported } from '@/utils/metamask';

const props = defineProps<{
  blockchain: Blockchain;
  inputMode: InputMode;
}>();

const emit = defineEmits<{
  (e: 'update:input-mode', mode: InputMode): void;
}>();
const { blockchain, inputMode } = toRefs(props);

const update = (value: InputMode) => emit('update:input-mode', value);

const { isEvm } = useSupportedChains();

const isSupportedEvmChain = isEvm(blockchain);
const isBitcoin = computed(() => isBtcChain(get(blockchain)));
const isMetaMask = computed(() => get(inputMode) === InputMode.METAMASK_IMPORT);

const metamaskDownloadLink = 'https://metamask.io/download/';

const copyPageUrl = async () => {
  const pageUrl = window.location.href;
  const { copy } = useClipboard({ source: pageUrl });
  await copy();
};

const { t } = useI18n();
const { isPackaged } = useInterop();
const { isAccountOperationRunning } = useAccountLoading();
const loading = isAccountOperationRunning();
</script>

<template>
  <div class="mb-5">
    <VBtnToggle
      :value="inputMode"
      class="input-mode-select"
      mandatory
      @change="update($event)"
    >
      <VBtn
        :value="InputMode.MANUAL_ADD"
        data-cy="input-mode-manual"
        :disabled="loading"
      >
        <RuiIcon name="pencil-line" />
        <span class="hidden-sm-and-down ml-2">
          {{ t('input_mode_select.manual_add.label') }}
        </span>
      </VBtn>
      <VBtn
        v-if="isSupportedEvmChain"
        :value="InputMode.METAMASK_IMPORT"
        :disabled="!isMetaMaskSupported() || loading"
      >
        <VImg
          contain
          max-width="24px"
          :src="`./assets/images/metamask-fox.svg`"
        />
        <span class="hidden-sm-and-down ml-2">
          {{ t('input_mode_select.metamask_import.label') }}
        </span>
      </VBtn>
      <VBtn v-if="isBitcoin" :value="InputMode.XPUB_ADD">
        <RuiIcon name="key-line" />
        <span class="hidden-sm-and-down ml-2">
          {{ t('input_mode_select.xpub_add.label') }}
        </span>
      </VBtn>
    </VBtnToggle>
    <p
      v-if="isSupportedEvmChain && isMetaMask"
      class="mt-3 info--text text-caption"
      v-text="t('input_mode_select.metamask_import.metamask')"
    />
    <div
      v-if="isSupportedEvmChain && !isPackaged && !isMetaMaskSupported()"
      class="mt-3 text-rui-warning text-caption flex items-center"
    >
      {{ t('input_mode_select.metamask_import.missing') }}

      <VMenu open-on-hover right offset-x close-delay="400" max-width="300">
        <template #activator="{ on }">
          <div v-on="on">
            <RuiIcon class="px-1" name="question-line" />
          </div>
        </template>
        <div class="pa-4 text-caption">
          <div>
            {{ t('input_mode_select.metamask_import.missing_tooltip.title') }}
          </div>
          <ol class="list-disc [&_li]:-ml-3">
            <li>
              <i18n
                path="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_installed"
              >
                <template #link>
                  <ExternalLink :url="metamaskDownloadLink">
                    {{ t('common.here') }}
                  </ExternalLink>
                </template>
              </i18n>
            </li>
            <li>
              {{
                t(
                  'input_mode_select.metamask_import.missing_tooltip.metamask_is_not_enabled'
                )
              }}
            </li>
            <li>
              <i18n
                path="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_supported_by_browser"
              >
                <template #link>
                  <ExternalLink :url="metamaskDownloadLink">
                    {{ t('common.here') }}
                  </ExternalLink>
                </template>

                <template #copy>
                  <a href="#" @click="copyPageUrl()">
                    {{
                      t(
                        'input_mode_select.metamask_import.missing_tooltip.copy_url'
                      )
                    }}
                  </a>
                </template>
              </i18n>
            </li>
          </ol>
        </div>
      </VMenu>
    </div>
  </div>
</template>
