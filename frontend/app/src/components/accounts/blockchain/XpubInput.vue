<template>
  <div>
    <v-row align="center" no-gutters class="mt-2">
      <v-col cols="auto">
        <v-select
          v-model="xpubKeyPrefix"
          outlined
          class="account-form__xpub-key-type"
          item-value="value"
          item-text="label"
          :disabled="disabled"
          :items="keyType"
        />
      </v-col>
      <v-col>
        <v-text-field
          v-model="xpubKey"
          outlined
          class="account-form__xpub ml-2"
          :label="$t('account_form.labels.btc.xpub')"
          autocomplete="off"
          :error-messages="errorMessages[fields.XPUB]"
          :disabled="disabled"
          @paste="onPasteXpub"
        >
          <template #append-outer>
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div class="account-form__advanced">
                  <v-btn
                    icon
                    v-bind="attrs"
                    v-on="on"
                    @click="advanced = !advanced"
                  >
                    <v-icon v-if="advanced">mdi-chevron-up</v-icon>
                    <v-icon v-else>mdi-chevron-down</v-icon>
                  </v-btn>
                </div>
              </template>
              <span>
                {{ $tc('account_form.advanced_tooltip', advanced ? 0 : 1) }}
              </span>
            </v-tooltip>
          </template>
        </v-text-field>
      </v-col>
    </v-row>
    <v-row v-if="advanced" no-gutters>
      <v-col>
        <v-text-field
          v-model="derivationPath"
          outlined
          class="account-form__derivation-path"
          :label="$t('account_form.labels.btc.derivation_path')"
          :error-messages="errorMessages[fields.DERIVATION_PATH]"
          autocomplete="off"
          :disabled="disabled"
          persistent-hint
          :hint="$t('account_form.labels.btc.derivation_path_hint')"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import {
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs,
  unref,
  watch
} from '@vue/composition-api';
import {
  getKeyType,
  getPrefix,
  keyType,
  XpubPrefix
} from '@/components/accounts/blockchain/xpub';
import { XpubPayload } from '@/store/balances/types';
import { trimOnPaste } from '@/utils/event';

const FIELD_XPUB = 'xpub';
const FIELD_DERIVATION_PATH = 'derivation_path';

export default defineComponent({
  name: 'XpubInput',
  props: {
    disabled: { required: true, type: Boolean },
    errorMessages: {
      required: true,
      type: Object as PropType<Record<string, string[]>>
    },
    xpub: {
      required: false,
      default: null,
      type: Object as PropType<XpubPayload>
    }
  },
  emits: ['update:xpub'],
  setup(props, { emit }) {
    const { xpub } = toRefs(props);
    const xpubKey = ref('');
    const derivationPath = ref('');
    const xpubKeyPrefix = ref<XpubPrefix>(XpubPrefix.XPUB);
    const advanced = ref(false);

    const updateXpub = (event: XpubPayload | null) => {
      emit('update:xpub', event);
    };
    const fields = {
      XPUB: FIELD_XPUB,
      DERIVATION_PATH: FIELD_DERIVATION_PATH
    };

    const isPrefixed = (value: string) => value.match(/([xzy]pub)(.*)/);
    const setXpubKeyType = (value: string) => {
      const match = isPrefixed(value);
      if (match && match.length === 3) {
        const prefix = match[1] as XpubPrefix;
        if (prefix === XpubPrefix.XPUB) {
          return;
        }
        xpubKeyPrefix.value = prefix;
      }
    };

    watch(xpub, xpub => {
      xpubKey.value = xpub?.xpub;
      xpubKeyPrefix.value = getPrefix(xpub?.xpubType);
      derivationPath.value = xpub?.derivationPath;
    });

    onMounted(() => {
      const payload = unref(xpub);
      xpubKey.value = payload?.xpub;
      xpubKeyPrefix.value = getPrefix(payload?.xpubType);
      derivationPath.value = payload?.derivationPath;
    });

    watch([xpubKeyPrefix, xpubKey, derivationPath], ([prefix, xpub, path]) => {
      if (xpub) {
        setXpubKeyType(xpub);
      }

      let payload: XpubPayload | null = null;
      if (xpub) {
        payload = {
          xpub: xpub.trim(),
          derivationPath: path ?? undefined,
          xpubType: getKeyType(prefix as XpubPrefix)
        };
      }
      updateXpub(payload);
    });

    const onPasteXpub = (event: ClipboardEvent) => {
      const paste = trimOnPaste(event);
      if (paste) {
        setXpubKeyType(paste);
        xpubKey.value = paste;
      }
    };

    return {
      xpubKey,
      xpubKeyPrefix,
      derivationPath,
      keyType,
      advanced,
      fields,
      onPasteXpub
    };
  }
});
</script>
