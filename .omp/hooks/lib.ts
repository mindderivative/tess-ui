/**
 * Shared by the project's omp hooks (`pre/` and `post/` next to this file; omp loads only those two folders, so this file is a plain module).
 *
 * The hooks are the omp form of the Claude Code hooks this project used to register in `.claude/settings.json`, which omp does not run.
 * Tests: `node --experimental-strip-types .omp/hooks/test_hooks.ts`.
 */

import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { delimiter, isAbsolute, join, resolve } from "node:path";

export interface RunResult {
	/** The exit code; 1 when the program could not start. */
	code: number;
	/** Standard output then standard error, as written (not trimmed). */
	out: string;
	timedOut: boolean;
}

export function run(file: string, args: string[], options: { cwd: string; timeoutMs: number }): Promise<RunResult> {
	return new Promise((done) => {
		execFile(file, args, { cwd: options.cwd, timeout: options.timeoutMs, maxBuffer: 4 << 20, killSignal: "SIGKILL" }, (error: any, stdout: string, stderr: string) => {
			const out = `${stdout}${stderr}`;
			if (!error) return done({ code: 0, out, timedOut: false });
			done({ code: typeof error.code === "number" ? error.code : 1, out: out || String(error.message ?? error), timedOut: error.killed === true });
		});
	});
}

function onPath(name: string): string | null {
	for (const dir of String(process.env.PATH ?? "").split(delimiter)) {
		if (dir && existsSync(join(dir, name))) return join(dir, name);
	}
	return null;
}

/** The project's ruff (`.venv/bin/ruff`), else the one on PATH, else `null`. */
export function ruffBin(cwd: string): string | null {
	const venv = join(cwd, ".venv", "bin", "ruff");
	return existsSync(venv) ? venv : onPath("ruff");
}

/** The project's Python (`.venv/bin/python`), or `null` (the tests need the project's own environment). */
export function venvPython(cwd: string): string | null {
	const venv = join(cwd, ".venv", "bin", "python");
	return existsSync(venv) ? venv : null;
}

/** Git options that take the next word as their value: `git -C dir push`. */
const GIT_OPTIONS_WITH_VALUE = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env", "--attr-source"]);

/**
 * The subcommand of every `git` in a shell command line (`git -C x push` is `push`), wherever it is: after `;`, `&&`, `|`, in `bash -c '...'`.
 * A `git` that is only text (`git log --grep push` is `log`; `echo "git push"` is `push`) is counted: a false alarm asks the user, a miss lets a push through.
 */
export function gitSubcommands(command: string): string[] {
	const found: string[] = [];
	const at = /(?:^|[\s;&|(`'"])git(?=\s)/g;
	for (let match = at.exec(command); match; match = at.exec(command)) {
		const words = command.slice(match.index + match[0].length).split(/\s+/).filter(Boolean);
		for (let i = 0; i < words.length; i++) {
			const word = words[i].replace(/^["'`(]+|["'`;&|)]+$/g, "");
			if (GIT_OPTIONS_WITH_VALUE.has(word)) {
				i++;
				continue;
			}
			if (word.startsWith("-")) continue;
			if (word) found.push(word);
			break;
		}
	}
	return found;
}

/** The files an `edit` or `write` call changed, as absolute paths (a relative one is the session's directory's). */
export function editedFiles(toolName: string, input: any, cwd: string): string[] {
	if (toolName !== "edit" && toolName !== "write") return [];
	const given: unknown[] = Array.isArray(input?.paths) ? input.paths : input?.path !== undefined ? [input.path] : [];
	const files = given.filter((p): p is string => typeof p === "string" && p !== "").map((p) => (isAbsolute(p) ? p : resolve(cwd, p)));
	return [...new Set(files)];
}

/** A `tool_result` patch that keeps the tool's own content and adds a report after it. */
export function withReport(event: any, report: string): { content: unknown[] } {
	return { content: [...(Array.isArray(event?.content) ? event.content : []), { type: "text", text: `\n${report}` }] };
}

/** `path` relative to `cwd` with `/`, or `null` when it is outside. */
export function insideProject(path: string, cwd: string): string | null {
	const root = resolve(cwd);
	const full = resolve(path);
	if (full !== root && !full.startsWith(root + "/")) return null;
	return full.slice(root.length + 1);
}
