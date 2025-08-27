import { logger } from '@/utils/logging';

/**
 * Standardized error handling utility for message handlers
 * Converts unknown errors to string format with proper logging
 */
export function handleMessageError(error: unknown, context: string): string {
  let errorMessage: string;

  if (error instanceof Error) {
    errorMessage = error.message;
  }
  else if (typeof error === 'string') {
    errorMessage = error;
  }
  else if (error && typeof error === 'object' && 'message' in error) {
    errorMessage = String((error as { message: unknown }).message);
  }
  else {
    errorMessage = 'Unknown error occurred';
  }

  logger.error(`${context}:`, errorMessage, error);
  return errorMessage;
}

/**
 * Logs handler errors with context but doesn't throw
 * Use for non-critical errors that shouldn't break message processing
 */
export function logHandlerError(error: unknown, context: string): void {
  handleMessageError(error, context);
}
