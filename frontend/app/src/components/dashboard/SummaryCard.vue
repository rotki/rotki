<template>
  <v-card
    :loading="isLoading"
    :class="`dashboard__summary-card__${name}`"
    class="pb-3"
  >
    <v-card-title
      class="
        font-weight-medium
        text-capitalize
        pa-3
        secondary--text
        summary-card__header
      "
    >
      <card-title :class="navigatesTo ? 'summary-card--navigates' : null">
        <span @click="navigatesTo ? navigate() : null">
          {{ $t('summary_card.title', { name }) }}
        </span>
      </card-title>
      <v-tooltip v-if="$slots.tooltip" bottom max-width="300px">
        <template #activator="{ on }">
          <v-icon
            small
            class="mb-3 ml-1 summary-card__header__tooltip"
            v-on="on"
          >
            mdi-information-circle
          </v-icon>
        </template>
        <div>
          <slot name="tooltip" />
        </div>
      </v-tooltip>
      <v-spacer />
      <span>
        <v-tooltip v-if="canRefresh" bottom max-width="300px">
          <template #activator="{ on }">
            <v-btn
              icon
              x-small
              :disabled="isLoading"
              color="primary"
              class="summary-card__refresh-icon"
              @click="refresh(name)"
              v-on="on"
            >
              <v-icon color="primary">mdi-refresh</v-icon>
            </v-btn>
          </template>
          <span>{{ $t('summary_card.refresh_tooltip', { name }) }}</span>
        </v-tooltip>
      </span>
    </v-card-title>
    <v-list>
      <slot />
    </v-list>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class SummaryCard extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: false, default: false })
  isLoading!: boolean;
  @Prop({ required: false, default: false, type: Boolean })
  canRefresh!: boolean;
  @Prop({ required: false, default: '', type: String })
  navigatesTo!: string;

  refresh(balanceSource: string) {
    this.$emit('refresh', balanceSource.toLowerCase());
  }

  navigate() {
    this.$router.push({
      path: this.navigatesTo
    });
  }
}
</script>

<style scoped lang="scss">
.summary-card {
  &--navigates {
    cursor: pointer;
  }

  .v-list-item {
    font-size: 0.8em;
    max-height: 48px;
  }

  &__refresh-icon {
    filter: grayscale(100%);
    padding: 1rem;

    &:hover {
      filter: grayscale(0);
    }
  }

  &__header {
    &__tooltip {
      visibility: hidden;
    }

    &:hover {
      .summary-card {
        &__header {
          &__tooltip {
            visibility: visible;
          }
        }
      }
    }
  }
}
</style>
