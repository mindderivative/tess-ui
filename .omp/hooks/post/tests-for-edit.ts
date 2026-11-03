/**
 * After an edit or write under `src/tesserae/` or `tests/`: run the tests `tools/tests_for.py` picks for the changed files (the Claude Code hook
 * `tests_for_edit.sh`). Silent when they pass or none is picked; a failure adds the end of the output after the tool's own result.
 *
 * omp gives a handler 30 seconds, where the Claude Code hook had 50, so the run is capped at 25: a run that is cut off says so and is not a failure.
 * `tests_for.py` stops at the first failing test (`pytest -x`); the tests it names are the ones that cover the change, never the whole suite.
 */

import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { editedFiles, insideProject, run, venvPython, withReport } from "../lib.ts";

export const TIMEOUT_MS = 25_000;

/** A shipped source or view file, or a test file. */
export const SELECTED = /\/src\/tesserae\/.*\.(py|yaml)$|\/tests\/test_[^/]*\.py$/;

export async function failuresIn(files: string[], cwd: string, timeoutMs = TIMEOUT_MS): Promise<string | null> {
	const mine = files.filter((file) => SELECTED.test(file) && insideProject(file, cwd) !== null);
	if (mine.length === 0) return null;
	const python = venvPython(cwd);
	if (!python) return null;
	const ran = await run(python, ["-I", "tools/tests_for.py", "--run", ...mine], { cwd, timeoutMs });
	if (ran.timedOut) {
		return `tests_for: the picked tests for ${mine.map((f) => insideProject(f, cwd)).join(", ")} ran past ${Math.round(timeoutMs / 1000)} seconds; run them by hand: python3 -I tools/tests_for.py --run`;
	}
	if (ran.code === 0) return null;
	return `tests_for: the tests that cover this change failed:\n${ran.out.trim().split("\n").slice(-40).join("\n")}`;
}

export default function (pi: ExtensionAPI) {
	pi.on("tool_result", async (event: any, ctx: any) => {
		try {
			if (event.isError) return undefined;
			const report = await failuresIn(editedFiles(event.toolName, event.input, ctx.cwd), ctx.cwd);
			return report ? withReport(event, report) : undefined;
		} catch {
			return undefined;
		}
	});
}
