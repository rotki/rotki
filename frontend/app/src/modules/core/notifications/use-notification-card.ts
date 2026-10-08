import type { ComputedRef, CSSProperties, MaybeRefOrGetter, Ref } from 'vue';
import { type NotificationAction, type NotificationData, NotificationKind, Severity } from '@rotki/common';
import { isRuiIcon, type RuiIcons } from '@rotki/ui-library';
import { arrayify } from '@/modules/core/common/data/array';
import { useSharedClipboard } from '@/modules/core/common/use-clipboard';

/** Height in pixels beyond which the message is collapsed behind an expand arrow. */
export const NOTIFICATION_MAX_HEIGHT = 64;

const REMINDER_TONE = 'reminder';

/** How a card is coloured: by its severity, or as a reminder. */
type CardTone = Severity | typeof REMINDER_TONE;

interface UseNotificationCardOptions {
  /** Measured height of the message body; drives whether the expand arrow is offered. */
  height: MaybeRefOrGetter<number>;
  /** Called when an action asks for the notification to go away. */
  dismiss: (id: number) => void;
}

interface UseNotificationCardReturn {
  /** The notification's actions, always a list even when it carries a single one. */
  actions: ComputedRef<NotificationAction[]>;
  /** Toggles the message between collapsed and expanded. */
  buttonClicked: () => void;
  /** Soft tinted disc and glyph colour of the severity icon. */
  circleBgClass: ComputedRef<string>;
  /** Semantic colour of the card: its severity, or `reminder` for a reminder. */
  color: ComputedRef<string>;
  /** Severity-tinted border of the card, which itself stays on the plain surface. */
  colorBgClass: ComputedRef<string>;
  /** Puts the message on the clipboard, resolving the i18n parameters first. */
  copy: () => Promise<void>;
  /**
   * Runs an action and dismisses the notification unless the action persists.
   *
   * @remarks
   * The dismissal is the action's own doing rather than the user's, so a `persist` action is the
   * only way to leave the card on screen after it runs.
   */
  doAction: (action: NotificationAction) => void;
  /** Gradient target of the expand button, matching the card background. */
  expandButtonClass: ComputedRef<string>;
  /** Whether the message is currently showing in full. */
  expanded: Readonly<Ref<boolean>>;
  /** Falls back to a generic arrow when an action names an icon the library does not have. */
  getIcon: (action: NotificationAction) => RuiIcons;
  /** Severity icon shown in the circle. */
  icon: ComputedRef<RuiIcons>;
  /** Expands the message; a message short enough to fit is already showing in full. */
  messageClicked: () => void;
  /** Height constraint applied to the message wrapper while it is collapsed. */
  messageWrapperStyle: ComputedRef<CSSProperties>;
  /** Whether the message overflows and so offers the expand arrow. */
  showExpandArrow: ComputedRef<boolean>;
  /**
   * When the notification arrived, in milliseconds.
   *
   * @remarks
   * Rebuilt through `new Date` rather than read off the field, so a notification that has been
   * through a serialization boundary and come back with a string date still renders. Phase 3 of
   * rotki#12942 persists the needs-you ones across sessions, which is exactly that boundary.
   */
  timestamp: ComputedRef<number>;
}

/**
 * Drives a single notification card: its severity styling, and the expand and action behaviour
 * behind it.
 *
 * @returns the derived presentation and the three things a user can do to the card
 */
export function useNotificationCard(
  notification: MaybeRefOrGetter<NotificationData>,
  options: UseNotificationCardOptions,
): UseNotificationCardReturn {
  const { dismiss, height } = options;

  const { copy: copyToClipboard } = useSharedClipboard();

  const expanded = shallowRef<boolean>(false);

  const actions = computed<NotificationAction[]>(() => {
    const action = toValue(notification).action;

    if (!action)
      return [];

    return arrayify(action);
  });

  /** A reminder is styled as one whatever its severity; anything else by its severity. */
  const tone = computed<CardTone>(() => {
    const { kind, severity } = toValue(notification);
    return kind === NotificationKind.REMINDER ? REMINDER_TONE : severity;
  });

  const icon = computed<RuiIcons>(() => {
    switch (get(tone)) {
      case Severity.ERROR:
      case Severity.INFO:
        return 'lu-circle-alert';
      case Severity.WARNING:
        return 'lu-siren';
      case REMINDER_TONE:
        return 'lu-alarm-clock';
    }
  });

  const color = computed<string>(() => get(tone));

  const colorBgClass = computed<string>(() => {
    switch (get(color)) {
      case 'warning':
        return 'border-rui-warning-border';
      case 'error':
        return 'border-rui-error-border';
      case 'info':
        return 'border-rui-info-border';
      case REMINDER_TONE:
        return 'border-rui-secondary-border';
      default:
        return '';
    }
  });

  // the card is on the surface in every severity, so the clamped message fades into it
  const expandButtonClass = computed<string>(() => 'to-rui-surface');

  const circleBgClass = computed<string>(() => {
    switch (get(tone)) {
      case Severity.ERROR:
        return 'bg-rui-error-soft text-rui-error';
      case Severity.INFO:
        return 'bg-rui-info-soft text-rui-info';
      case Severity.WARNING:
        return 'bg-rui-warning-soft text-rui-warning';
      case REMINDER_TONE:
        return 'bg-rui-secondary-soft text-rui-secondary';
    }
  });

  const timestamp = computed<number>(() => new Date(toValue(notification).date).getTime());

  const showExpandArrow = computed<boolean>(() => toValue(height) > NOTIFICATION_MAX_HEIGHT);

  const messageWrapperStyle = computed<CSSProperties>(() => {
    if (!get(showExpandArrow))
      return {};

    const usedHeight = get(expanded) ? toValue(height) : NOTIFICATION_MAX_HEIGHT;
    return {
      height: `${usedHeight}px`,
    };
  });

  async function copy(): Promise<void> {
    await copyToClipboard(toValue(notification).message);
  }

  function doAction(action: NotificationAction): void {
    action.action?.();
    if (!action.persist)
      dismiss(toValue(notification).id);
  }

  function messageClicked(): void {
    set(expanded, true);
  }

  function buttonClicked(): void {
    set(expanded, !get(expanded));
  }

  function getIcon(action: NotificationAction): RuiIcons {
    return isRuiIcon(action.icon) ? action.icon : 'lu-arrow-right';
  }

  return {
    actions,
    buttonClicked,
    circleBgClass,
    color,
    colorBgClass,
    copy,
    doAction,
    expandButtonClass,
    expanded: readonly(expanded),
    getIcon,
    icon,
    messageClicked,
    messageWrapperStyle,
    showExpandArrow,
    timestamp,
  };
}
