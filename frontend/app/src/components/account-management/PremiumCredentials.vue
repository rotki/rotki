<template>
  <div>
    <v-row no-gutters>
      <v-checkbox
        :value="enabled"
        :label="$t('premium_credentials.label_enable')"
        @change="enabledChanged"
      />
      <v-tooltip bottom max-width="400px">
        <template #activator="{ on }">
          <v-icon small class="mb-3 ml-1" v-on="on">fa fa-info-circle</v-icon>
        </template>
        <span>
          {{ $t('premium_credentials.tooltip') }}
        </span>
      </v-tooltip>
    </v-row>
    <div v-if="enabled">
      <revealable-input
        :value="apiKey"
        :disabled="loading"
        class="premium-settings__fields__api-key"
        :rules="apiKeyRules"
        :label="$t('premium_credentials.label_api_key')"
        @input="apiKeyChanged"
        @paste="onApiKeyPaste"
      />
      <revealable-input
        :value="apiSecret"
        :disabled="loading"
        class="premium-settings__fields__api-secret"
        prepend-icon="mdi-lock"
        :label="$t('premium_credentials.label_api_secret')"
        :rules="apiSecretRules"
        @input="apiSecretChanged"
        @paste="onApiSecretPaste"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { trimOnPaste } from '@/utils/event';

@Component({
  components: { RevealableInput }
})
export default class PremiumCredentials extends Vue {
  @Prop({ required: true })
  loading!: boolean;
  @Prop({ required: true })
  enabled!: boolean;
  @Prop({ required: true })
  apiSecret!: string;
  @Prop({ required: true })
  apiKey!: string;

  showKey: boolean = false;
  showSecret: boolean = false;

  @Watch('enabled')
  onEnabledChange() {
    if (!this.enabled) {
      this.apiKeyChanged('');
      this.apiSecretChanged('');
    }
  }

  readonly apiKeyRules = [
    (v: string) =>
      !!v || this.$t('premium_credentials.validation.non_empty_key')
  ];
  readonly apiSecretRules = [
    (v: string) =>
      !!v || this.$t('premium_credentials.validation.non_empty_secret')
  ];

  @Emit()
  apiKeyChanged(_apiKey: string) {}

  @Emit()
  apiSecretChanged(_apiSecret: string) {}

  @Emit()
  enabledChanged(_enabled: boolean) {}

  onApiKeyPaste(_event: ClipboardEvent) {
    const paste = trimOnPaste(_event);
    if (paste) {
      this.apiKeyChanged(paste);
    }
  }

  onApiSecretPaste(_event: ClipboardEvent) {
    const paste = trimOnPaste(_event);
    if (paste) {
      this.apiSecretChanged(paste);
    }
  }
}
</script>
