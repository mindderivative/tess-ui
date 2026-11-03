/**
 * After an edit or write: a pyflakes-level ruff check (syntax errors, unused or undefined names) of the Python files under `src/` or `tools/` that
 * the call changed (the Claude Code hook `ruff_edit.sh`). Report only: no auto-fix, since an unused import may be a re-export. Silent when clean.
 * The report is added after the tool's own result, so the model and the transcript both show it.
 */

import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { editedFiles, insideProject, ruffBin, run, withReport } from "../lib.ts";

/** A Python file under a `src/` or `tools/` folder. */
export const CHECKED = /\/(src|tools)\/.*\.py$/;

export async function problemsIn(files: string[], cwd: string): Promise<string | null> {
	const mine = files.filter((file) => CHECKED.test(file) && insideProject(file, cwd) !== null);
	if (mine.length === 0) return null;
	const ruff = ruffBin(cwd);
	if (!ruff) return null;
	const checked = await run(ruff, ["check", "--isolated", "--select", "E9,F", "--quiet", ...mine], { cwd, timeoutMs: 20_000 });
	return checked.code === 0 ? null : `ruff (pyflakes level) found problems in the file just changed:\n${checked.out.trim()}`;
}

export default function (pi: ExtensionAPI) {
	pi.on("tool_result", async (event: any, ctx: any) => {
		try {
			if (event.isError) return undefined;
			const problems = await problemsIn(editedFiles(event.toolName, event.input, ctx.cwd), ctx.cwd);
			return problems ? withReport(event, problems) : undefined;
		} catch {
			return undefined; // a check that could not run is not worth an error
		}
	});
}
