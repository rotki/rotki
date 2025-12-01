import { checkIfDevelopment } from '@shared/utils';
import { FetchError, ofetch } from 'ofetch';
import { usePremium } from '@/composables/premium';
import { camelCaseTransformer } from '@/modules/api/transformers';
import { DashboardSchema, type VisibilityPeriod, WelcomeSchema } from '@/types/dynamic-messages';
import { logger } from '@/utils/logging';

export const serializer = {
  read: (v: any): any => (v ? JSON.parse(v) : null),
  write: (v: any): string => JSON.stringify(v),
};

export const useDynamicMessages = createSharedComposable(() => {
  const branch = checkIfDevelopment() ? 'develop' : 'main';
  const welcomeMessages = useSessionStorage<WelcomeSchema>('rotki.messages.welcome', null, {
    serializer,
  });
  const dashboardMessages = useSessionStorage<DashboardSchema>('rotki.messages.dashboard', null, {
    serializer,
  });

  const premium = usePremium();

  const welcomeHeader = computed(() => {
    if (!isDefined(welcomeMessages))
      return null;

    const { header, text } = get(welcomeMessages);

    return {
      header,
      text,
    };
  });

  const getValidMessages = <T extends { period: VisibilityPeriod }>(messages: T[]): T[] => {
    const now = Date.now() / 1000;

    return messages.filter(x => x.period.start <= now && x.period.end > now);
  };

  const getFirstValidMessage = <T extends { period: VisibilityPeriod }>(messages: T[]): T | null =>
    getValidMessages(messages)[0] ?? null;

  const welcomeMessage = computed(() => {
    if (!isDefined(welcomeMessages))
      return null;

    const { messages } = get(welcomeMessages);
    return getFirstValidMessage(messages);
  });

  const activeWelcomeMessages = computed(() => {
    if (!isDefined(welcomeMessages))
      return [];

    return getValidMessages(get(welcomeMessages).messages);
  });

  const activeDashboardMessages = computed(() => {
    if (!isDefined(dashboardMessages))
      return [];

    const isPremium = get(premium);
    const validMessages = getValidMessages(get(dashboardMessages));

    return validMessages.filter((message) => {
      // If target is 'free', only show to free users
      if (message.target === 'free' && isPremium)
        return false;

      // If target is 'premium', only show to premium users
      if (message.target === 'premium' && !isPremium)
        return false;

      return true;
    });
  });

  const getWelcomeData = async (): Promise<WelcomeSchema | null> => {
    try {
      const response = await ofetch<object>(
        `https://raw.githubusercontent.com/rotki/data/${branch}/messages/welcome.json`,
        { responseType: 'json' },
      );

      return WelcomeSchema.parse(camelCaseTransformer(response));
    }
    catch (error: any) {
      if (!(error instanceof FetchError))
        logger.error(error);

      return null;
    }
  };

  const getDashboardData = async (): Promise<DashboardSchema | null> => {
    try {
      const response = await ofetch<object>(
        `https://raw.githubusercontent.com/rotki/data/${branch}/messages/dashboard.json`,
        { responseType: 'json' },
      );
      return DashboardSchema.parse(camelCaseTransformer(response));
    }
    catch (error: any) {
      if (!(error instanceof FetchError))
        logger.error(error);

      return null;
    }
  };

  const fetchMessages = async (): Promise<void> => {
    set(welcomeMessages, await getWelcomeData());
    set(dashboardMessages, await getDashboardData());
  };

  return {
    activeDashboardMessages,
    activeWelcomeMessages,
    fetchMessages,
    welcomeHeader,
    welcomeMessage,
  };
});
