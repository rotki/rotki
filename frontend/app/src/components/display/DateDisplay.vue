<template>
  <span class="date-display">
    {{ timestamp | formatDate(dateDisplayFormat) }}
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';

@Component({
  computed: {
    ...mapGetters('session', ['dateDisplayFormat'])
  }
})
export default class DateDisplay extends Vue {
  @Prop({ required: true, type: Number })
  timestamp!: number;

  dateDisplayFormat!: string;
}
</script>

<style scoped></style>
