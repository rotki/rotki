import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';

/**
 * Standardized error handling utility for message handlers
 * Converts unknown errors to string format with proper logging
 */
export function handleMessageError(error: unknown, context: string): string {
  const errorMessage = getErrorMessage(error);
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
