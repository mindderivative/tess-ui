/**
 * Before a bash call: the one rule AGENTS.md sets for git, made a real check (the Claude Code hook `bash_guard.sh` did not run under omp).
 *
 *  - `git push` is the user's separate decision. With a person to ask, the call waits for a yes; without one (a subagent, `omp -p`) it is blocked.
 *  - `git commit` first checks the Python files the commit will hold at pyflakes level (syntax errors, unused or undefined names), so an old finding
 *    elsewhere does not block it; a finding blocks the commit and the report is the reason. The files are the staged ones, the ones a `git add` in the
 *    same command line would stage (`git add -n` says which: `git add x && git commit` is how commits are made, and nothing is staged when the hook
 *    runs), and with `commit -a` the tracked files that changed. The Claude Code hook checked only what was already staged, so it never saw those.
 *
 * Every `bash` call passes through here, a nested one (`tools.bash` in an eval cell) too. A throw in a `tool_call` handler blocks the tool,
 * so the lint half catches its own errors and lets the commit through; the push half does not: a push that cannot be asked about is blocked.
 */

import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { gitSubcommands, ruffBin, run } from "../lib.ts";
import { existsSync } from "node:fs";
import { join } from "node:path";

export const PUSH_BLOCKED = "Blocked: pushing needs a separate, human-gated instruction (AGENTS.md). Commit locally only.";

/** What a shell would expand, quote or substitute: an argument list with any of it cannot be given to `git add -n` as written. */
const SHELL_SPECIAL = /[$`(){}<>*?[\]"'\\]/;
/** `git [options] add <arguments up to the end of the command>`. */
const ADD = /\bgit\s+(?:(?:-C|-c)\s+\S+\s+|-\S+\s+)*add\b([^;&|\n]*)/g;
const COMMIT = /\bgit\s+(?:(?:-C|-c)\s+\S+\s+|-\S+\s+)*commit\b([^;&|\n]*)/g;
/** `-a`, `-am`, `-qa` or `--all` among a commit's arguments (not `--amend`). */
const ALL_FLAG = /(?:^|\s)(?:-[a-zA-Z]*a[a-zA-Z]*|--all)(?=\s|$)/;

const python = (names: string[]) => names.filter((name) => name.endsWith(".py"));

async function lines(cwd: string, args: string[]): Promise<string[]> {
	const done = await run("git", args, { cwd, timeoutMs: 10_000 });
	return done.code === 0 ? done.out.split("\n").filter(Boolean) : [];
}

/** The Python files a commit made by `command` in `cwd` would hold, relative to `cwd`. */
export async function commitFiles(command: string, cwd: string): Promise<string[]> {
	const files = new Set(python(await lines(cwd, ["diff", "--cached", "--name-only", "--relative", "--diff-filter=ACM"])));
	let everything = false; // a `git add` too odd to ask git about: take every changed or new Python file
	for (const add of command.matchAll(ADD)) {
		const args = add[1].trim();
		if (SHELL_SPECIAL.test(args)) {
			everything = true;
			continue;
		}
		for (const line of await lines(cwd, ["add", "-n", ...args.split(/\s+/).filter(Boolean)])) {
			const named = /^add '(.*)'$/.exec(line);
			if (named) files.add(named[1]);
		}
	}
	if ([...command.matchAll(COMMIT)].some((commit) => ALL_FLAG.test(commit[1]))) {
		for (const name of await lines(cwd, ["diff", "--name-only", "--relative", "--diff-filter=ACM"])) files.add(name);
	}
	if (everything) {
		for (const line of await lines(cwd, ["status", "--porcelain", "-uall"])) {
			if (line[1] === "D" || line[0] === "D") continue;
			files.add(line.slice(3).replace(/^.* -> /, ""));
		}
	}
	return python([...files]).filter((name) => existsSync(join(cwd, name)));
}

/** The ruff report for the Python files the commit would hold, or `null` when they are clean, there are none, or ruff is not there. */
export async function commitProblems(command: string, cwd: string): Promise<string | null> {
	const ruff = ruffBin(cwd);
	if (!ruff) return null;
	const files = await commitFiles(command, cwd);
	if (files.length === 0) return null;
	const checked = await run(ruff, ["check", "--isolated", "--select", "E9,F", "--quiet", ...files], { cwd, timeoutMs: 30_000 });
	return checked.code === 0 ? null : `ruff found problems in the Python files this commit would hold:\n${checked.out.trim()}`;
}

export async function guardBash(command: string, ctx: { cwd: string; hasUI?: boolean; ui?: { confirm: (title: string, message: string) => Promise<boolean> } }): Promise<{ block: true; reason: string } | undefined> {
	const subcommands = gitSubcommands(command);
	if (subcommands.includes("push")) {
		if (ctx.hasUI && ctx.ui) {
			const allowed = await ctx.ui.confirm("git push", `${command}\n\nPushing is a separate, human-gated step (AGENTS.md). Allow this push?`);
			if (allowed === true) return undefined;
			return { block: true, reason: `${PUSH_BLOCKED} The user did not allow this push.` };
		}
		return { block: true, reason: `${PUSH_BLOCKED} There is no one to ask in this session.` };
	}
	if (subcommands.includes("commit")) {
		try {
			const problems = await commitProblems(command, ctx.cwd);
			if (problems) return { block: true, reason: problems };
		} catch {
			// a lint that could not run must not stop a commit
		}
	}
	return undefined;
}

export default function (pi: ExtensionAPI) {
	pi.on("tool_call", async (event: any, ctx: any) => {
		if (event.toolName !== "bash") return undefined;
		return guardBash(String(event.input?.command ?? ""), ctx);
	});
}
