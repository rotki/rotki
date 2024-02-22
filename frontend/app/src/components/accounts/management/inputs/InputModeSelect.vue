<script setup lang="ts">
import { isBtcChain } from '@/types/blockchain/chains';
import { InputMode } from '@/types/input-mode';
import { isMetaMaskSupported } from '@/utils/metamask';
import { externalLinks } from '@/data/external-links';

const props = defineProps<{
  blockchain: string;
  inputMode: InputMode;
}>();

const emit = defineEmits<{
  (e: 'update:input-mode', mode: InputMode): void;
}>();
const { blockchain, inputMode } = toRefs(props);

const internalValue = computed({
  get() {
    return props.inputMode;
  },
  set(value: string) {
    assert(isOfEnum(InputMode)(value));
    emit('update:input-mode', value);
  },
});

const { isEvm } = useSupportedChains();

const isSupportedEvmChain = isEvm(blockchain);
const isBitcoin = computed(() => isBtcChain(get(blockchain)));
const isMetaMask = computed(() => get(inputMode) === InputMode.METAMASK_IMPORT);
const isXpub = computed(() => get(inputMode) === InputMode.XPUB_ADD);

const { metamaskDownload } = externalLinks;

async function copyPageUrl() {
  const pageUrl = window.location.href;
  const { copy } = useClipboard({ source: pageUrl });
  await copy();
}

const { t } = useI18n();
const { isPackaged } = useInterop();
const { isAccountOperationRunning } = useAccountLoading();
const loading = isAccountOperationRunning();

const invalidCombination = logicOr(
  logicAnd(logicNot(isSupportedEvmChain), isMetaMask),
  logicAnd(logicNot(isBitcoin), isXpub),
);

watch(invalidCombination, (invalid) => {
  if (invalid)
    emit('update:input-mode', InputMode.MANUAL_ADD);
});

onUnmounted(() => {
  emit('update:input-mode', InputMode.MANUAL_ADD);
});
</script>

<template>
  <div class="mb-5">
    <RuiButtonGroup
      v-model="internalValue"
      class="input-mode-select"
      variant="outlined"
      size="lg"
      required
      color="primary"
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
            <AppImage
              contain
              max-width="24px"
              src="./assets/images/metamask-fox.svg"
            />
          </template>
          <span class="hidden md:block">
            {{ t('input_mode_select.metamask_import.label') }}
          </span>
        </RuiButton>
        <RuiButton
          v-if="isBitcoin"
          type="button"
          :value="InputMode.XPUB_ADD"
          :disabled="loading"
        >
          <template #prepend>
            <RuiIcon name="key-line" />
          </template>
          <span class="hidden md:block">
            {{ t('input_mode_select.xpub_add.label') }}
          </span>
        </RuiButton>
      </template>
    </RuiButtonGroup>
    <div
      v-if="isSupportedEvmChain && isMetaMask"
      class="mt-3 text-rui-info text-caption"
      v-text="t('input_mode_select.metamask_import.metamask')"
    />
    <div
      v-if="isSupportedEvmChain && !isPackaged && !isMetaMaskSupported()"
      class="text-rui-warning text-caption flex items-center"
    >
      {{ t('input_mode_select.metamask_import.missing') }}

      <RuiMenu
        open-on-hover
        :close-delay="400"
        menu-class="max-w-[20rem]"
        :popper="{ placement: 'right-start' }"
      >
        <template #activator="{ on }">
          <RuiButton
            size="sm"
            variant="text"
            icon
            color="warning"
            v-on="on"
          >
            <RuiIcon
              class="px-1"
              name="question-line"
            />
          </RuiButton>
        </template>
        <div class="px-4 py-3 text-caption">
          <div>
            {{ t('input_mode_select.metamask_import.missing_tooltip.title') }}
          </div>
          <ol class="list-disc [&_li]:ml-3">
            <li>
              <i18n
                path="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_installed"
              >
                <template #link>
                  <ExternalLink
                    :url="metamaskDownload"
                    color="primary"
                  >
                    {{ t('common.here') }}
                  </ExternalLink>
                </template>
              </i18n>
            </li>
            <li>
              {{
                t(
                  'input_mode_select.metamask_import.missing_tooltip.metamask_is_not_enabled',
                )
              }}
            </li>
            <li>
              <i18n
                path="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_supported_by_browser"
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
                    class="inline-flex text-[1em] !p-0 !px-1 -mx-1"
                    @click="copyPageUrl()"
                  >
                    {{
                      t(
                        'input_mode_select.metamask_import.missing_tooltip.copy_url',
                      )
                    }}
                  </RuiButton>
                </template>
              </i18n>
            </li>
          </ol>
        </div>
      </RuiMenu>
    </div>
  </div>
</template>
