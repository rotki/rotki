<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
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

const isEth = computed(() => get(blockchain) === Blockchain.ETH);
const isBtc = computed(() => get(blockchain) === Blockchain.BTC);
const isBch = computed(() => get(blockchain) === Blockchain.BCH);
const isMetaMask = computed(() => get(inputMode) === InputMode.METAMASK_IMPORT);

const metamaskDownloadLink = 'https://metamask.io/download/';

const copyPageUrl = async () => {
  const pageUrl = window.location.href;
  const { copy } = useClipboard({ source: pageUrl });
  await copy();
};

const { t } = useI18n();
const { isPackaged } = useInterop();
</script>

<template>
  <div class="mb-5">
    <v-btn-toggle
      :value="inputMode"
      class="input-mode-select"
      mandatory
      @change="update($event)"
    >
      <v-btn :value="InputMode.MANUAL_ADD" data-cy="input-mode-manual">
        <v-icon>mdi-pencil-plus</v-icon>
        <span class="hidden-sm-and-down ml-1">
          {{ t('input_mode_select.manual_add.label') }}
        </span>
      </v-btn>
      <v-btn
        v-if="isEth"
        :value="InputMode.METAMASK_IMPORT"
        :disabled="!isMetaMaskSupported()"
      >
        <v-img
          contain
          max-width="24px"
          :src="`./assets/images/metamask-fox.svg`"
        />
        <span class="hidden-sm-and-down ml-1">
          {{ t('input_mode_select.metamask_import.label') }}
        </span>
      </v-btn>
      <v-btn v-if="isBtc || isBch" :value="InputMode.XPUB_ADD">
        <v-icon>mdi-key-plus</v-icon>
        <span class="hidden-sm-and-down ml-1">
          {{ t('input_mode_select.xpub_add.label') }}
        </span>
      </v-btn>
    </v-btn-toggle>
    <p
      v-if="isEth && isMetaMask"
      class="mt-3 info--text text-caption"
      v-text="t('input_mode_select.metamask_import.metamask')"
    />
    <div
      v-if="isEth && !isPackaged && !isMetaMaskSupported()"
      class="mt-3 warning--text text-caption"
    >
      {{ t('input_mode_select.metamask_import.missing') }}

      <v-menu open-on-hover right offset-x close-delay="400" max-width="300">
        <template #activator="{ on }">
          <v-icon class="px-1" small v-on="on">mdi-help-circle</v-icon>
        </template>
        <div class="pa-4 text-caption">
          <div>
            {{ t('input_mode_select.metamask_import.missing_tooltip.title') }}
          </div>
          <ol>
            <li>
              <i18n
                path="input_mode_select.metamask_import.missing_tooltip.metamask_is_not_installed"
              >
                <template #link>
                  <external-link :url="metamaskDownloadLink">
                    {{ t('common.here') }}
                  </external-link>
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
                  <external-link :url="metamaskDownloadLink">
                    {{ t('common.here') }}
                  </external-link>
                </template>

                <template #copy>
                  <a href="#" @click="copyPageUrl">
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
      </v-menu>
    </div>
  </div>
</template>
