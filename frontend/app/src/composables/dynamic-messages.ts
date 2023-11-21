import { AxiosError, type AxiosResponse } from 'axios';
import { api } from '@/services/rotkehlchen-api';
import {
  DashboardSchema,
  type VisibilityPeriod,
  WelcomeSchema
} from '@/types/dynamic-messages';
import { camelCaseTransformer } from '@/services/axios-tranformers';

const serializer = {
  read: (v: any) => (v ? JSON.parse(v) : null),
  write: (v: any) => JSON.stringify(v)
};

export const useDynamicMessages = createSharedComposable(() => {
  const welcomeMessages = useSessionStorage<WelcomeSchema>(
    'rotki.messages.welcome',
    null,
    {
      serializer
    }
  );
  const dashboardMessages = useSessionStorage<DashboardSchema>(
    'rotki.messages.dashboard',
    null,
    {
      serializer
    }
  );

  const welcomeHeader = computed(() => {
    if (!isDefined(welcomeMessages)) {
      return null;
    }

    const { header, text } = get(welcomeMessages);

    return {
      header,
      text
    };
  });

  const welcomeMessage = computed(() => {
    if (!isDefined(welcomeMessages)) {
      return null;
    }

    const { messages } = get(welcomeMessages);
    return getFirstValidMessage(messages);
  });

  const dashboardMessage = computed(() => {
    if (!isDefined(dashboardMessages)) {
      return null;
    }

    return getFirstValidMessage(get(dashboardMessages));
  });

  const getFirstValidMessage = <T extends { period: VisibilityPeriod }>(
    messages: T[]
  ): T | null => {
    const now = Date.now() / 1000;

    const validMessages = messages.filter(
      x => x.period.start <= now && x.period.end > now
    );
    if (validMessages.length === 0) {
      return null;
    }

    return validMessages[0];
  };

  const getData = <T>(response: AxiosResponse<T>) => {
    if (typeof response.data === 'string') {
      return camelCaseTransformer(JSON.parse(response.data));
    }
    return response.data;
  };

  const getWelcomeData = async (): Promise<WelcomeSchema | null> => {
    try {
      const response = await api.instance.get<WelcomeSchema>(
        'https://raw.githubusercontent.com/rotki/data/main/messages/welcome.json'
      );
      return WelcomeSchema.parse(getData(response));
    } catch (e: any) {
      if (!(e instanceof AxiosError)) {
        logger.error(e);
      }
      return null;
    }
  };

  const getDashboardData = async (): Promise<DashboardSchema | null> => {
    try {
      const response = await api.instance.get<DashboardSchema>(
        'https://raw.githubusercontent.com/rotki/data/main/messages/dashboard.json'
      );
      return DashboardSchema.parse(getData(response));
    } catch (e: any) {
      if (!(e instanceof AxiosError)) {
        logger.error(e);
      }

      return null;
    }
  };

  const fetchMessages = async () => {
    set(welcomeMessages, await getWelcomeData());
    set(dashboardMessages, await getDashboardData());
  };

  return {
    fetchMessages,
    welcomeHeader,
    welcomeMessage,
    dashboardMessage
  };
});
