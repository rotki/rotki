import type { ComputedRef, CSSProperties, MaybeRefOrGetter, Ref } from 'vue';
import { type NotificationAction, type NotificationData, Severity } from '@rotki/common';
import { isRuiIcon, type RuiIcons } from '@rotki/ui-library';
import dayjs from 'dayjs';
import { arrayify } from '@/modules/core/common/data/array';

/** Height in pixels beyond which the message is collapsed behind an expand arrow. */
export const NOTIFICATION_MAX_HEIGHT = 64;

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
  /** Background of the severity circle. */
  circleBgClass: ComputedRef<string>;
  /** Semantic colour of the card, which an action overrides to a warning. */
  color: ComputedRef<string>;
  /** Tinted card background matching {@link UseNotificationCardReturn.color}. */
  colorBgClass: ComputedRef<string>;
  /** Puts the message on the clipboard, resolving the i18n parameters first. */
  copy: () => Promise<void>;
  /** The notification's date in the locale's long format. */
  date: ComputedRef<string>;
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
}

/**
 * Drives a single notification card: its severity styling, its date, and the expand and action
 * behaviour behind it.
 *
 * @returns the derived presentation and the three things a user can do to the card
 */
export function useNotificationCard(
  notification: MaybeRefOrGetter<NotificationData>,
  options: UseNotificationCardOptions,
): UseNotificationCardReturn {
  const { dismiss, height } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { copy: copyToClipboard } = useClipboard();

  const expanded = shallowRef<boolean>(false);

  const actions = computed<NotificationAction[]>(() => {
    const action = toValue(notification).action;

    if (!action)
      return [];

    return arrayify(action);
  });

  const icon = computed<RuiIcons>(() => {
    switch (toValue(notification).severity) {
      case Severity.ERROR:
      case Severity.INFO:
        return 'lu-circle-alert';
      case Severity.WARNING:
        return 'lu-siren';
      case Severity.REMINDER:
        return 'lu-alarm-clock';
      default:
        return 'lu-circle-alert';
    }
  });

  const color = computed<string>(() => {
    const data = toValue(notification);
    if (data.action)
      return 'warning';

    switch (data.severity) {
      case Severity.ERROR:
        return 'error';
      case Severity.INFO:
        return 'info';
      case Severity.WARNING:
        return 'warning';
      case Severity.REMINDER:
        return 'reminder';
      default:
        return '';
    }
  });

  const colorBgClass = computed<string>(() => {
    switch (get(color)) {
      case 'warning':
        return '!bg-rui-warning/10';
      case 'error':
        return '!bg-rui-error/10';
      case 'info':
        return '!bg-rui-info/10';
      case 'reminder':
        return '!bg-rui-secondary/10';
      default:
        return '';
    }
  });

  const expandButtonClass = computed<string>(() => {
    switch (get(color)) {
      case 'warning':
        return '!to-rui-warning/10';
      case 'error':
        return '!to-rui-error/10';
      case 'info':
        return '!to-rui-info/10';
      case 'reminder':
        return '!to-rui-secondary/10';
      default:
        return '';
    }
  });

  const circleBgClass = computed<string>(() => {
    switch (toValue(notification).severity) {
      case Severity.ERROR:
        return 'bg-rui-error';
      case Severity.INFO:
        return 'bg-rui-info';
      case Severity.WARNING:
        return 'bg-rui-warning';
      case Severity.REMINDER:
        return 'bg-rui-secondary';
      default:
        return 'bg-rui-success';
    }
  });

  const date = computed<string>(() => dayjs(toValue(notification).date).format('LLL'));

  const showExpandArrow = computed<boolean>(() => toValue(height) > NOTIFICATION_MAX_HEIGHT);

  const messageWrapperStyle = computed<CSSProperties>(() => {
    if (!get(showExpandArrow))
      return {};

    const usedHeight = get(expanded) ? toValue(height) + 24 : NOTIFICATION_MAX_HEIGHT;
    return {
      height: `${usedHeight}px`,
    };
  });

  async function copy(): Promise<void> {
    const { i18nParam, message } = toValue(notification);
    let messageText = message;

    if (i18nParam) {
      messageText = t(i18nParam.message, {
        location: i18nParam.props.location,
        service: i18nParam.props.service,
        url: i18nParam.props.url,
      });
    }
    await copyToClipboard(messageText);
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
    date,
    doAction,
    expandButtonClass,
    expanded: readonly(expanded),
    getIcon,
    icon,
    messageClicked,
    messageWrapperStyle,
    showExpandArrow,
  };
}
