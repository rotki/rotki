import { z } from 'zod/v4';

const Action = z.object({
  text: z.string(),
  url: z.string(),
});

const VisibilityPeriod = z.object({
  end: z.number().positive(),
  start: z.number().positive(),
});

export type VisibilityPeriod = z.infer<typeof VisibilityPeriod>;

const WelcomeMessage = z.object({
  action: Action.optional(),
  header: z.string().optional(),
  icon: z.string().optional(),
  period: VisibilityPeriod,
  text: z.string(),
});

export type WelcomeMessage = z.infer<typeof WelcomeMessage>;

export const WelcomeSchema = z.object({
  header: z.string().optional(),
  messages: z.array(WelcomeMessage),
  text: z.string().optional(),
});

export type WelcomeSchema = z.infer<typeof WelcomeSchema>;

const DashboardMessage = z.object({
  action: Action.optional(),
  message: z.string(),
  messageHighlight: z.string().optional(),
  period: VisibilityPeriod,
});

export type DashboardMessage = z.infer<typeof DashboardMessage>;

export const DashboardSchema = z.array(DashboardMessage);

export type DashboardSchema = z.infer<typeof DashboardSchema>;
