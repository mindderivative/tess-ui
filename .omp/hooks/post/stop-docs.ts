/**
 * When the agent is about to stop: if `src/` has uncommitted Python changes and no documentation changed, ask once for the documentation update
 * AGENTS.md requires (the Claude Code hook `stop_docs.sh`). `session_stop` is omp's stop hook: `{ continue: true, additionalContext }` asks the agent to
 * go on with that text. It asks once per prompt, and not at all when this stop is already the answer to a stop hook (`stop_hook_active`).
 * The graph refresh the Claude Code Stop hook also did is the user-level graphify extension's job (`~/.omp/agent/extensions/graphify`).
 */

import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { run } from "../lib.ts";

export const ASK =
	"src/ has uncommitted changes but CHANGELOG.md, LOG.md and docs/ do not. Update the documentation (AGENTS.md policy), or say why none is needed.";

/** The ask, or `null` when source did not change, or documentation did too. */
export async function docsReminder(cwd: string): Promise<string | null> {
	// -uall: a new untracked folder is listed file by file, not as `?? src/`, which would hide the Python file in it
	const status = await run("git", ["status", "--porcelain", "-uall"], { cwd, timeoutMs: 8_000 });
	if (status.code !== 0) return null;
	if (!/ src\/.*\.py$/m.test(status.out)) return null;
	if (/ (docs\/|CHANGELOG\.md|LOG\.md)/m.test(status.out)) return null;
	return ASK;
}

export default function (pi: ExtensionAPI) {
	let asked = false;
	pi.on("before_agent_start", async () => {
		asked = false; // each prompt is asked at most once
	});
	pi.on("session_stop", async (event: any, ctx: any) => {
		try {
			if (asked || event?.stop_hook_active === true) return undefined;
			const text = await docsReminder(ctx.cwd);
			if (!text) return undefined;
			asked = true;
			return { continue: true, additionalContext: text };
		} catch {
			return undefined;
		}
	});
}
