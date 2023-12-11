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
const isXpub = computed(() => get(inputMode) === InputMode.XPUB_ADD);

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

const invalidCombination = logicOr(
  logicAnd(logicNot(isSupportedEvmChain), isMetaMask),
  logicAnd(logicNot(isBitcoin), isXpub)
);

watch(invalidCombination, invalid => {
  if (invalid) {
    update(InputMode.MANUAL_ADD);
  }
});

onUnmounted(() => {
  update(InputMode.MANUAL_ADD);
});
</script>

<template>
  <div class="mb-5">
    <RuiButtonGroup
      :value="inputMode"
      class="input-mode-select"
      variant="outlined"
      size="lg"
      required
      color="primary"
      @input="update($event)"
    >
      <template #default>
        <RuiButton
          type="button"
          :value="InputMode.MANUAL_ADD"
          data-cy="input-mode-manual"
          :disabled="loading"
        >
          <template #prepend>
            <RuiIcon name="pencil-line" />
          </template>
          <span class="hidden md:block">
            {{ t('input_mode_select.manual_add.label') }}
          </span>
        </RuiButton>
        <RuiButton
          v-if="isSupportedEvmChain"
          type="button"
          :value="InputMode.METAMASK_IMPORT"
          :disabled="!isMetaMaskSupported() || loading"
        >
          <template #prepend>
            <VImg
              contain
              max-width="24px"
              :src="`./assets/images/metamask-fox.svg`"
            />
          </template>
          <span class="hidden md:block">
            {{ t('input_mode_select.metamask_import.label') }}
          </span>
        </RuiButton>
        <RuiButton v-if="isBitcoin" type="button" :value="InputMode.XPUB_ADD">
          <template #prepend>
            <RuiIcon name="key-line" />
          </template>
          <span class="hidden md:block">
            {{ t('input_mode_select.xpub_add.label') }}
          </span>
        </RuiButton>
      </template>
    </RuiButtonGroup>
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

      <VMenu open-on-hover right offset-x :close-delay="400" max-width="300">
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
