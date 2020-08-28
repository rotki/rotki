<template>
  <v-row align="center">
    <v-col cols="auto">
      <v-tooltip top>
        <template #activator="{ on, attrs }">
          <v-btn
            color="primary"
            depressed
            v-bind="{ ...attrs, ...$attrs }"
            v-on="{ ...on, ...$listeners }"
          >
            <slot />
          </v-btn>
        </template>
        <span>{{ tooltip }}</span>
      </v-tooltip>
    </v-col>
    <v-col v-if="!!successMessage">
      <v-icon color="success">fa-check-circle</v-icon>
      <span class="ml-2 success--text status-button__message--success">
        {{ successMessage }}
      </span>
    </v-col>
    <v-col v-else-if="!!errorMessage">
      <v-icon color="error">fa-warning</v-icon>
      <span class="ml-2 error--text status-button__message--error">
        {{ errorMessage }}
      </span>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class StatusButton extends Vue {
  @Prop({ required: true })
  successMessage!: string;
  @Prop({ required: true })
  errorMessage!: string;
  @Prop({ required: false, type: String, default: '' })
  tooltip!: string;
}
</script>
