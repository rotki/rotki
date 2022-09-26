<template>
  <div class="mb-5">
    <v-btn-toggle
      :value="value"
      class="input-mode-select"
      mandatory
      @change="input($event)"
    >
      <v-btn :value="MANUAL_ADD" data-cy="input-mode-manual">
        <v-icon>mdi-pencil-plus</v-icon>
        <span class="hidden-sm-and-down ml-1">
          {{ t('input_mode_select.manual_add.label') }}
        </span>
      </v-btn>
      <v-btn
        v-if="isEth"
        :value="METAMASK_IMPORT"
        :disabled="!isMetaMaskSupported()"
      >
        <v-img
          contain
          max-width="24px"
          :src="`/assets/images/metamask-fox.svg`"
        />
        <span class="hidden-sm-and-down ml-1">
          {{ t('input_mode_select.metamask_import.label') }}
        </span>
      </v-btn>
      <v-btn v-if="isBtc || isBch" :value="XPUB_ADD">
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
                  <a
                    :class="$style.link"
                    target="_blank"
                    :href="metamaskDownloadLink"
                  >
                    {{
                      t(
                        'input_mode_select.metamask_import.missing_tooltip.here'
                      )
                    }}
                  </a>
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
                  <a
                    :class="$style.link"
                    target="_blank"
                    :href="metamaskDownloadLink"
                  >
                    {{
                      t(
                        'input_mode_select.metamask_import.missing_tooltip.here'
                      )
                    }}
                  </a>
                </template>

                <template #copy>
                  <a :class="$style.link" @click="copyPageUrl">
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

<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import { useInterop } from '@/electron-interop';
import {
  AccountInput,
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/types/account-input';
import { isMetaMaskSupported } from '@/utils/metamask';

const props = defineProps({
  blockchain: {
    required: true,
    type: String as PropType<Blockchain>,
    validator: (value: any) => Object.values(Blockchain).includes(value)
  },
  value: { required: true, type: String as PropType<AccountInput> }
});

const emit = defineEmits(['input']);
const { blockchain, value } = toRefs(props);

const input = (value: AccountInput) => emit('input', value);

const isEth = computed(() => get(blockchain) === Blockchain.ETH);
const isBtc = computed(() => get(blockchain) === Blockchain.BTC);
const isBch = computed(() => get(blockchain) === Blockchain.BCH);
const isMetaMask = computed(() => get(value) === METAMASK_IMPORT);

const metamaskDownloadLink = 'https://metamask.io/download/';

const copyPageUrl = async () => {
  const params = new URLSearchParams(window.location.search);
  params.set('add', 'true');
  params.set('test', 'false');

  const { origin, pathname } = window.location;

  const pageUrl = `${origin}${pathname}?${params}`;
  const { copy } = useClipboard({ source: pageUrl });
  await copy();
};

const { t } = useI18n();
const { isPackaged } = useInterop();
</script>
<style lang="css" module>
.link {
  font-weight: bold;
  text-decoration: none;
}
</style>
