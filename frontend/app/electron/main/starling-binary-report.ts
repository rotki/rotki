import type { LogService } from '@electron/main/log-service';
import type { StarlingErrorListener } from '@electron/main/starling-handler-types';
import type { UnusableBinary } from '@shared/starling/binary-types';
import { BackendCode } from '@shared/ipc';
import { findUnusableBinary, refusedStarling } from '@shared/starling/binary-health';

/** How often, and how many times, a lost binary is looked for after an unexplained failure. */
const LOST_BINARY_RECHECK_MS = 2000;
const LOST_BINARY_RECHECKS = 5;

/**
 * Keeps looking for a lost binary for a while after the backend failed with every file in place.
 *
 * @remarks
 * Antivirus kills the process before it quarantines the file, and the two need not land together.
 * When the file is still there as the failure is reported, the user is shown the generic message,
 * and without a later look nothing would ever tell them it was the file. The report this makes
 * replaces the generic screen in the renderer.
 */
class LostBinaryWatch {
  private timer: ReturnType<typeof setInterval> | undefined;

  /** @param found - checks once and returns whether the binary was found gone and reported. */
  start(found: () => boolean): void {
    this.stop();
    let remaining = LOST_BINARY_RECHECKS;
    this.timer = setInterval(() => {
      remaining -= 1;
      if (found() || remaining <= 0)
        this.stop();
    }, LOST_BINARY_RECHECK_MS);
  }

  stop(): void {
    clearInterval(this.timer);
    this.timer = undefined;
  }
}

/**
 * The one door every backend failure is reported through, so that each is blamed on a lost binary
 * whenever one explains it.
 *
 * @remarks
 * A binary that vanishes mid-session is the same incident as one already gone at startup, and a
 * kill by antivirus can exit 0, so neither the moment nor the exit code tells them apart: only the
 * file's absence does. Dev builds are skipped: they launch core through an interpreter and colibri
 * through cargo, so there is no shipped binary to lose.
 */
export class BackendFailureReport {
  private readonly watch = new LostBinaryWatch();
  /** The core binary the running starling was launched with, see {@link findUnusableBinary}. */
  private launchedCore: string | undefined;
  /** Whether this failure was already reported, so a follow-up exit does not bury the first, more specific message. */
  private reported: boolean = false;
  /** Whether this failure was already blamed on a binary, so the crash and the exit that follows report it once. */
  private blamed: boolean = false;

  constructor(private readonly logger: LogService, private readonly isDev: boolean) {}

  /** Records the core binary a new starling is launched with, taken from its `--core-binary` argument. */
  launched(args: string[]): void {
    const flag = args.indexOf('--core-binary');
    this.launchedCore = flag === -1 ? undefined : args[flag + 1];
  }

  /** Starts over for a restart in place: ends any watch and forgets the last failure, keeping the launched core. */
  restarting(): void {
    this.watch.stop();
    this.reported = false;
    this.blamed = false;
  }

  /** Starts over for a fresh launch or a deliberate stop, forgetting the launched core too. */
  reset(): void {
    this.restarting();
    this.launchedCore = undefined;
  }

  /**
   * Whether one of the bundled executables is gone or unusable, reported to the listener when it
   * is. Once this failure was blamed on a binary it answers yes without reporting it again.
   */
  binaryLost(listener: StarlingErrorListener): boolean {
    if (this.isDev)
      return false;
    if (this.blamed)
      return true;

    const unusable = findUnusableBinary(this.launchedCore);
    if (!unusable)
      return false;

    this.blame(unusable, listener);
    return true;
  }

  /**
   * A backend failure: blamed on a lost or refused binary when one explains it, otherwise reported
   * as given and then watched, in case the file goes after all.
   */
  failed(message: string | Error, listener: StarlingErrorListener): void {
    this.reported = true;
    if (this.binaryLost(listener) || this.starlingRefused(message, listener))
      return;

    listener.onProcessError(message, BackendCode.TERMINATED);
    this.watchForLoss(listener);
  }

  /**
   * starling exited 0 without being asked to.
   *
   * @remarks
   * That is also how it ends on a signal (Ctrl+C, logoff, system shutdown), so nothing is reported
   * unless a binary is gone. Antivirus can kill with code 0 and quarantine the file a moment later,
   * so the binaries are watched for a while too. A real quit ends the watch through
   * {@link BackendFailureReport.reset}, and the watch only reports a file that is actually gone.
   */
  exitedUnasked(listener: StarlingErrorListener): void {
    if (!this.binaryLost(listener))
      this.watchForLoss(listener);
  }

  private watchForLoss(listener: StarlingErrorListener): void {
    if (!this.isDev)
      this.watch.start(() => this.binaryLost(listener));
  }

  /** Whether a spawn error means the system refused to start starling, reported to the listener when it does. */
  private starlingRefused(error: string | Error, listener: StarlingErrorListener): boolean {
    const refused = this.isDev ? undefined : refusedStarling(error);
    if (!refused)
      return false;

    this.blame(refused, listener);
    return true;
  }

  /**
   * Reports the failure as the binary's.
   *
   * @remarks
   * The text is a fallback for logs and for anywhere that only has a string; the renderer draws
   * its screen from the structured report instead.
   */
  private blame(unusable: UnusableBinary, listener: StarlingErrorListener): void {
    this.blamed = true;
    this.logger.error(`Bundled binary ${unusable.component} is ${unusable.status}: ${unusable.path}`);
    listener.onProcessError(
      `The rotki component '${unusable.component}' is ${unusable.status}: ${unusable.path}`,
      BackendCode.MISSING_BINARY,
      unusable,
    );
  }

  /**
   * {@link BackendFailureReport.failed}, unless this failure was already reported, in which case
   * only the binary check runs. starling exits after a service crash it already announced, and the
   * generic exit text must not replace the crash's own reason.
   */
  failedUnlessReported(message: string, listener: StarlingErrorListener): void {
    if (this.reported)
      this.binaryLost(listener);
    else
      this.failed(message, listener);
  }
}
