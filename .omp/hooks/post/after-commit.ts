/**
 * After a bash call that made a local commit: the reminder AGENTS.md's memory and board policy asks for (the Claude Code hook `after_commit.sh`).
 * It is passive guidance for the next step, not part of the tool's output, and only a commit that succeeded gets it.
 */

import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { gitSubcommands } from "../lib.ts";

export const REMINDER =
	"A local commit finished. Per AGENTS.md: if it changed a decision, a lesson, a standing instruction or the project's status, update the single `Tesserae` " +
	"memory entity in place (back up ~/.claude-memory/memory.jsonl to ~/.claude/memory-backups/ before pruning). If it finished a board issue, run " +
	'`python3 tools/board.py move N "In review" --comment "..."`. Do not log the commit itself.';

export default function (pi: ExtensionAPI) {
	pi.on("tool_result", async (event: any) => {
		if (event.toolName !== "bash" || event.isError) return undefined;
		if (!gitSubcommands(String(event.input?.command ?? "")).includes("commit")) return undefined;
		return { additionalContext: REMINDER };
	});
}
