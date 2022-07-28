<template>
  <div>
    <v-dialog v-if="info.total > 0" width="500">
      <template #activator="{ on }">
        <a
          class="pa-4"
          :class="{ 'text-decoration-underline': info.total > 0 }"
          v-on="on"
        >
          {{ info.total }}
        </a>
      </template>
      <v-card :loading="loading">
        <div class="d-flex justify-space-between align-center px-2">
          <v-card-title>
            <card-title>
              {{
                $t('account_balances.detect_tokens.title', {
                  length: info.total
                })
              }}
            </card-title>
          </v-card-title>
          <div>
            <v-tooltip top>
              <template #activator="{ on }">
                <v-btn
                  text
                  icon
                  :disabled="disabled"
                  v-on="on"
                  @click="refresh"
                >
                  <v-progress-circular
                    v-if="loading"
                    indeterminate
                    color="primary"
                    width="2"
                    size="20"
                  />
                  <v-icon v-else>mdi-refresh</v-icon>
                </v-btn>
              </template>
              <div class="text-center">
                <div>
                  {{ $t('account_balances.detect_tokens.tooltip.redetect') }}
                </div>
                <div v-if="info.timestamp">
                  <i18n
                    path="account_balances.detect_tokens.tooltip.last_detected"
                  >
                    <template #time>
                      <date-display :timestamp="info.timestamp" />
                    </template>
                  </i18n>
                </div>
              </div>
            </v-tooltip>
          </div>
        </div>
        <div class="pb-2">
          <div :class="$style.wrapper">
            <div v-for="token in info.tokens" :key="token">
              <asset-details opens-details :asset="token" />
            </div>
          </div>
        </div>
      </v-card>
    </v-dialog>
    <div v-else class="pa-4">
      {{ info.total }}
    </div>
  </div>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { EthDetectedTokensInfo } from '@/services/balances/types';

export default defineComponent({
  name: 'AccountDetectedTokensDialog',
  props: {
    info: {
      required: true,
      type: Object as PropType<EthDetectedTokensInfo>
    },
    disabled: {
      required: false,
      type: Boolean,
      default: false
    },
    loading: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  emits: ['refresh'],
  setup(_, { emit }) {
    const refresh = () => {
      emit('refresh');
    };

    return {
      refresh
    };
  }
});
</script>
<style module lang="scss">
.wrapper {
  padding: 0 1.5rem;
  max-height: calc(100vh - 200px);
  overflow: auto;
}
</style>
