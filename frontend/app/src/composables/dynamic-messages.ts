import { checkIfDevelopment } from '@shared/utils';
import { AxiosError, type AxiosResponse } from 'axios';
import { camelCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
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

    return getValidMessages(get(dashboardMessages));
  });

  const getData = <T>(response: AxiosResponse<T>): T => {
    if (typeof response.data === 'string')
      return camelCaseTransformer(JSON.parse(response.data));

    return response.data;
  };

  const getWelcomeData = async (): Promise<WelcomeSchema | null> => {
    try {
      const response = await api.instance.get<WelcomeSchema>(
        `https://raw.githubusercontent.com/rotki/data/${branch}/messages/welcome.json`,
      );
      return WelcomeSchema.parse(getData(response));
    }
    catch (error: any) {
      if (!(error instanceof AxiosError))
        logger.error(error);

      return null;
    }
  };

  const getDashboardData = async (): Promise<DashboardSchema | null> => {
    try {
      const response = await api.instance.get<DashboardSchema>(
        `https://raw.githubusercontent.com/rotki/data/${branch}/messages/dashboard.json`,
      );
      return DashboardSchema.parse(getData(response));
    }
    catch (error: any) {
      if (!(error instanceof AxiosError))
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
