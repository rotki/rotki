<template>
  <span class="date-display" :class="privacyMode ? 'blur-content' : null">
    {{ timestamp | formatDate(dateDisplayFormat) }}
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';

@Component({
  computed: {
    ...mapGetters('session', ['dateDisplayFormat']),
    ...mapState('session', ['privacyMode'])
  }
})
export default class DateDisplay extends Vue {
  @Prop({ required: true, type: Number })
  timestamp!: number;

  dateDisplayFormat!: string;
  privacyMode!: boolean;
}
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
