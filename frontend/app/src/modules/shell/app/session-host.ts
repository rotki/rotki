import { useSessionHost } from '@/modules/shell/app/use-session-host';

/**
 * Renders nothing: it exists to own the live session's monitor. `App.vue` renders one per session,
 * keyed on the session, so each session builds its own and the previous one is disposed.
 */
export const SessionHost = defineComponent({
  name: 'SessionHost',
  setup(): () => null {
    useSessionHost();
    return () => null;
  },
});
