import type { LogService } from '@electron/main/log-service';

export interface RendererShutdownDeps {
  /** Send the "app closing" notice to the renderer. Returns false if there is no live window to notify. */
  send: () => boolean;
  /** Register a one-shot ack listener. Returns a function that unregisters it. */
  waitForAck: (onAck: () => void) => () => void;
  logger: Pick<LogService, 'debug' | 'warn'>;
}

/**
 * Notifies the renderer that the app is about to quit and waits for it to
 * acknowledge (after halting its outbound traffic).
 *
 * Invariant: this resolves in at most `timeoutMs`, no matter what the renderer
 * does. The ack can only ever shorten the wait; it can never block or extend
 * shutdown. Resolves early when there is no renderer to notify. Never rejects.
 */
export async function notifyRendererOfShutdown(
  deps: RendererShutdownDeps,
  timeoutMs = 750,
): Promise<void> {
  let sent = false;
  try {
    sent = deps.send();
  }
  catch (error) {
    deps.logger.warn('Failed to notify renderer of shutdown', error);
    return;
  }

  if (!sent) {
    deps.logger.debug('No renderer to notify of shutdown; proceeding');
    return;
  }

  await new Promise<void>((resolve) => {
    let settled = false;
    let unregister = (): void => {};
    let timer: ReturnType<typeof setTimeout>;

    const finish = (reason: 'ack' | 'timeout'): void => {
      if (settled)
        return;
      settled = true;
      clearTimeout(timer);
      unregister();
      deps.logger.debug(`Renderer shutdown wait finished: ${reason}`);
      resolve();
    };

    // Arm the timeout unconditionally so a dead or unresponsive renderer can
    // never keep us waiting past timeoutMs.
    timer = setTimeout(() => finish('timeout'), timeoutMs);

    try {
      unregister = deps.waitForAck(() => finish('ack'));
    }
    catch (error) {
      deps.logger.warn('Failed to register shutdown ack listener', error);
      finish('timeout');
    }
  });
}
