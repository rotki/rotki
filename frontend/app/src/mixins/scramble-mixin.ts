import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';

@Component({
  computed: {
    ...mapState('session', ['scrambleData'])
  }
})
export default class ScrambleMixin extends Vue {
  scrambleData!: boolean;
}
