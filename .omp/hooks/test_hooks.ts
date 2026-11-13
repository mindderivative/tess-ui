/** Tests for the hooks in pre/ and post/. Run: node --experimental-strip-types .omp/hooks/test_hooks.ts   (uses the real git and ruff, and the real tests_for once) */
import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { editedFiles, gitSubcommands, insideProject, ruffBin, withReport } from "./lib.ts";
import gitGuard, { commitFiles, commitProblems, guardBash, PUSH_BLOCKED } from "./pre/git-guard.ts";
import afterCommit, { REMINDER } from "./post/after-commit.ts";
import ruffEdit, { problemsIn } from "./post/ruff-edit.ts";
import testsForEdit, { failuresIn } from "./post/tests-for-edit.ts";
import stopDocs, { ASK, docsReminder } from "./post/stop-docs.ts";

const PROJECT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const made: string[] = [];
const scratch = () => {
	const dir = mkdtempSync(join(tmpdir(), "omp-hooks-"));
	made.push(dir);
	return dir;
};
const git = (cwd: string, ...args: string[]) => execFileSync("git", args, { cwd, stdio: "pipe" });
const repo = () => {
	const dir = scratch();
	git(dir, "init", "-q");
	return dir;
};
const put = (dir: string, path: string, text: string) => {
	mkdirSync(dirname(join(dir, path)), { recursive: true });
	writeFileSync(join(dir, path), text);
};

/** The handlers a hook registers, by event, in order. */
function load(hook: (pi: any) => void) {
	const handlers: Record<string, Function[]> = {};
	hook({ on: (name: string, fn: Function) => (handlers[name] ??= []).push(fn) });
	return handlers;
}

assert.ok(ruffBin(tmpdir()), "these tests need ruff, in .venv or on PATH");

// -- which hook listens to what
assert.deepEqual(Object.keys(load(gitGuard)), ["tool_call"]);
assert.deepEqual(Object.keys(load(afterCommit)), ["tool_result"]);
assert.deepEqual(Object.keys(load(ruffEdit)), ["tool_result"]);
assert.deepEqual(Object.keys(load(testsForEdit)), ["tool_result"]);
assert.deepEqual(Object.keys(load(stopDocs)).sort(), ["before_agent_start", "session_stop"]);

// -- finding git in a command line
for (const [command, expected] of [
	["git push", ["push"]],
	["git push origin main", ["push"]],
	["git -C /some/dir push", ["push"]],
	["git -c user.name=x -C y push --force", ["push"]],
	["git --no-pager log", ["log"]],
	["cd x && git status; git push", ["status", "push"]],
	["bash -c 'git push origin'", ["push"]],
	['sh -c "git commit -m x"', ["commit"]],
	["GIT_TERMINAL_PROMPT=0 git push", ["push"]],
	["git log --grep push", ["log"]],
	["git stash push", ["stash"]],
	["git commit -m 'a'", ["commit"]],
	["echo hi", []],
	["digit push", []],
	["pgit push", []],
	["", []],
] as [string, string[]][]) {
	assert.deepEqual(gitSubcommands(command), expected, command);
}

// -- the files an edit changed
assert.deepEqual(editedFiles("write", { path: "a/b.py", content: "x" }, "/p"), ["/p/a/b.py"]);
assert.deepEqual(editedFiles("edit", { input: "[a.py#1]", path: "a.py", paths: ["a.py", "/abs/c.py", "a.py"] }, "/p"), ["/p/a.py", "/abs/c.py"]);
assert.deepEqual(editedFiles("edit", { input: "x", path: "a.py" }, "/p"), ["/p/a.py"]);
assert.deepEqual(editedFiles("bash", { command: "ls" }, "/p"), []);
assert.deepEqual(editedFiles("edit", {}, "/p"), []);
assert.equal(insideProject("/p/src/a.py", "/p"), "src/a.py");
assert.equal(insideProject("/q/src/a.py", "/p"), null);
assert.equal(insideProject("/p2/src/a.py", "/p"), null, "a sibling with the same prefix is outside");
assert.deepEqual(withReport({ content: [{ type: "text", text: "ok" }] }, "problem").content, [{ type: "text", text: "ok" }, { type: "text", text: "\nproblem" }]);

// -- git push runs without asking; a force push and a push of tags are blocked
{
	const headless = { cwd: "/p", hasUI: false };
	for (const command of ["git push", "git push origin main", "git push -u origin feat/colour-picker", "cd x && git -C y push origin main", "git push origin main feat/x"]) {
		assert.equal(await guardBash(command, headless), undefined, `${command} runs, with no one to ask`);
	}
	for (const command of ["git push --force", "git push -f origin main", "git push --force-with-lease", "git push origin +main", "git push --tags", "git push --follow-tags", "git push origin v1.0.0 --tag", "git push origin tag v1.0", "git push origin refs/tags/v1", "git push --delete origin x", "git push --mirror"]) {
		const refused = await guardBash(command, { cwd: "/p", hasUI: true });
		assert.equal(refused?.block, true, `${command} is blocked`);
		assert.match(refused!.reason, new RegExp(PUSH_BLOCKED.slice(0, 30)));
	}
	assert.equal(await guardBash("git status", headless as any), undefined);
	assert.equal(await guardBash("git log --grep=force", headless as any), undefined);
	assert.equal(await guardBash("ls -la", { cwd: "/p" }), undefined);
	const guard = load(gitGuard).tool_call[0];
	assert.equal(await guard({ toolName: "read", input: { path: "git push --force" } }, { cwd: "/p" }), undefined, "only bash is looked at");
	assert.equal((await guard({ toolName: "bash", input: { command: "git push --force" } }, { cwd: "/p", hasUI: false })).block, true);
	assert.equal(await guard({ toolName: "bash", input: { command: "git push origin main" } }, { cwd: "/p", hasUI: false }), undefined);
}

// -- git commit: the Python files the commit would hold are checked at pyflakes level
{
	const dir = repo();
	put(dir, "bad.py", "import os\n");
	put(dir, "good.py", "import os\nprint(os.name)\n");
	put(dir, "notes.txt", "x\n");
	const reason = /ruff found problems in the Python files this commit would hold/;
	assert.deepEqual(await commitFiles("git commit -m x", dir), [], "nothing staged, nothing added");
	assert.equal(await commitProblems("git commit -m x", dir), null);

	// staged by an earlier call
	git(dir, "add", "good.py");
	assert.deepEqual(await commitFiles("git commit -m x", dir), ["good.py"]);
	assert.equal(await guardBash("git commit -m x", { cwd: dir }), undefined, "a clean staged file");
	git(dir, "add", "bad.py");
	const staged = await guardBash("git commit -m x", { cwd: dir });
	assert.equal(staged?.block, true);
	assert.match(staged!.reason, reason);
	assert.match(staged!.reason, /bad\.py/);
	assert.match(staged!.reason, /F401/);
	git(dir, "reset", "-q", "bad.py");

	// staged by the same command line: how commits are made, and nothing is staged yet when the hook runs
	assert.deepEqual(await commitFiles("git add good.py && git commit -m x", dir), ["good.py"]);
	const together = await guardBash("git add bad.py && git commit -m x", { cwd: dir });
	assert.equal(together?.block, true, "the file the command stages is checked");
	assert.match(together!.reason, /bad\.py/);
	assert.equal((await guardBash("git add -A && git commit -m x", { cwd: dir }))?.block, true, "-A stages it too");
	assert.equal((await guardBash("git add . ; git commit -m x", { cwd: dir }))?.block, true, "so does .");
	assert.equal((await guardBash("git -C . add bad.py && git -C . commit -m x", { cwd: dir }))?.block, true, "with git's own options");
	assert.equal(await guardBash("git add good.py && git commit -m x", { cwd: dir }), undefined, "an unrelated file that is not added does not block");
	assert.equal(await guardBash("git add notes.txt && git commit -m x", { cwd: dir }), undefined, "no Python added");
	assert.equal((await guardBash("git add b* && git commit -m x", { cwd: dir }))?.block, true, "an argument the hook cannot hand to git: every changed Python file is checked");
	assert.equal((await guardBash('git add "bad.py" && git commit -m x', { cwd: dir }))?.block, true, "quoted, the same");

	// commit -a stages the tracked files that changed
	git(dir, "add", "good.py", "bad.py");
	git(dir, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--no-verify", "-m", "start");
	assert.equal(await guardBash("git commit -m x", { cwd: dir }), undefined, "nothing changed");
	put(dir, "bad.py", "import sys\n");
	assert.equal(await guardBash("git commit -m x", { cwd: dir }), undefined, "changed but not staged and no -a: not in this commit");
	for (const flag of ["-a", "-am", "--all", "-qa"]) {
		assert.equal((await guardBash(`git commit ${flag} "m"`, { cwd: dir }))?.block, true, flag);
	}
	assert.equal(await guardBash('git commit --amend -m "a"', { cwd: dir }), undefined, "--amend is not -a");

	assert.equal(await commitProblems("git commit -m x", scratch()), null, "not a repository: no verdict, no block");
	const clean = repo();
	put(clean, "notes.txt", "x");
	git(clean, "add", "notes.txt");
	assert.equal(await guardBash("git commit -m x", { cwd: clean }), undefined, "no Python staged");
}

// -- after a commit: the reminder, for a commit that worked
{
	const h = load(afterCommit).tool_result[0];
	const ok = await h({ toolName: "bash", isError: false, input: { command: 'git commit -m "x"' } });
	assert.equal(ok.additionalContext, REMINDER);
	assert.match(REMINDER, /Tesserae/);
	assert.match(REMINDER, /board\.py move/);
	assert.equal(await h({ toolName: "bash", isError: true, input: { command: "git commit -m x" } }), undefined, "a failed commit is not a commit");
	assert.equal(await h({ toolName: "bash", isError: false, input: { command: "git status" } }), undefined);
	assert.equal(await h({ toolName: "read", isError: false, input: { path: "git commit" } }), undefined);
}

// -- after an edit: pyflakes on src/ and tools/ Python
{
	const dir = scratch();
	put(dir, "src/m.py", "import os\n");
	put(dir, "src/ok.py", "import os\nprint(os.name)\n");
	put(dir, "docs/x.py", "import os\n");
	assert.match((await problemsIn([join(dir, "src/m.py")], dir))!, /F401/);
	assert.equal(await problemsIn([join(dir, "src/ok.py")], dir), null);
	assert.equal(await problemsIn([join(dir, "docs/x.py")], dir), null, "only src/ and tools/");
	assert.equal(await problemsIn(["/elsewhere/src/m.py"], dir), null, "only this project");
	const h = load(ruffEdit).tool_result[0];
	const event = { toolName: "write", isError: false, input: { path: "src/m.py", content: "import os\n" }, content: [{ type: "text", text: "Successfully wrote" }] };
	const patched = await h(event, { cwd: dir });
	assert.equal(patched.content.length, 2, "the tool's own result is kept, the report follows");
	assert.equal(patched.content[0].text, "Successfully wrote");
	assert.match(patched.content[1].text, /found problems in the file just changed/);
	assert.equal(await h({ ...event, isError: true }, { cwd: dir }), undefined);
	assert.equal(await h({ ...event, input: { path: "src/ok.py", content: "" } }, { cwd: dir }), undefined, "a clean file says nothing");
	assert.equal(await h({ toolName: "bash", isError: false, input: { command: "ls" }, content: [] }, { cwd: dir }), undefined);
}

// -- after an edit: the tests that cover it (a fake python, to see each outcome)
{
	const fake = (script: string) => {
		const dir = scratch();
		mkdirSync(join(dir, ".venv", "bin"), { recursive: true });
		writeFileSync(join(dir, ".venv", "bin", "python"), `#!/bin/sh\n${script}\n`);
		chmodSync(join(dir, ".venv", "bin", "python"), 0o755);
		return dir;
	};
	const failing = fake('echo "args: $@"; echo "FAILED tests/test_x.py::test_a"; exit 1');
	const text = await failuresIn([join(failing, "src/tess_ui/a.py")], failing);
	assert.match(text!, /the tests that cover this change failed/);
	assert.match(text!, /FAILED tests\/test_x\.py::test_a/);
	assert.match(text!, /-I tools\/tests_for\.py --run .*src\/tess_ui\/a\.py/, "the changed file is what tests_for is asked about");
	const passing = fake("exit 0");
	assert.equal(await failuresIn([join(passing, "src/tess_ui/a.py")], passing), null, "silent when they pass");
	assert.equal(await failuresIn([join(passing, "tests/test_a.py")], passing), null);
	assert.equal(await failuresIn([join(failing, "docs/index.md")], failing), null, "a docs file runs nothing");
	assert.match((await failuresIn([join(failing, "src/tess_ui/views/Button_View.yaml")], failing))!, /failed/, "a shipped view counts");
	assert.equal(await failuresIn([join(failing, "tools/a.py")], failing), null, "tools/ is for the lint, not the tests");
	const slow = fake("sleep 5");
	assert.match((await failuresIn([join(slow, "src/tess_ui/a.py")], slow, 200))!, /ran past \d+ seconds; run them by hand/, "a cut-off run says so");
	assert.equal(await failuresIn([join(scratch(), "src/tess_ui/a.py")], scratch()), null, "no venv: nothing to run with");
	const h = load(testsForEdit).tool_result[0];
	const event = { toolName: "edit", isError: false, input: { input: "x", path: "src/tess_ui/a.py", paths: ["src/tess_ui/a.py"] }, content: [{ type: "text", text: "[a.py#1]" }] };
	const patched = await h(event, { cwd: failing });
	assert.equal(patched.content[0].text, "[a.py#1]");
	assert.match(patched.content[1].text, /failed/);
	assert.equal(await h({ ...event, isError: true }, { cwd: failing }), undefined);
	// the real thing: this project's own tests_for on a test file that passes
	assert.equal(await failuresIn([join(PROJECT, "tests", "test_wrong_kind.py")], PROJECT), null, "tests_for ran test_wrong_kind.py and it passed");
}

// -- at stop: documentation, asked once per prompt
{
	const dir = repo();
	assert.equal(await docsReminder(dir), null, "nothing changed");
	put(dir, "src/a.py", "x = 1\n");
	assert.equal(await docsReminder(dir), ASK, "source changed, no documentation");
	put(dir, "docs/x.md", "x\n");
	assert.equal(await docsReminder(dir), null, "documentation changed too");
	const other = repo();
	put(other, "src/data.yaml", "a: 1\n");
	assert.equal(await docsReminder(other), null, "not Python");
	put(other, "LOG.md", "x\n");
	put(other, "src/b.py", "y = 2\n");
	assert.equal(await docsReminder(other), null, "LOG.md counts");
	assert.equal(await docsReminder(scratch()), null, "not a repository");

	const fresh = repo();
	put(fresh, "src/a.py", "x = 1\n");
	const h = load(stopDocs);
	const stop = h.session_stop[0];
	const ctx = { cwd: fresh };
	const first = await stop({ stop_hook_active: false }, ctx);
	assert.deepEqual(first, { continue: true, additionalContext: ASK });
	assert.equal(await stop({ stop_hook_active: false }, ctx), undefined, "once per prompt");
	await h.before_agent_start[0]({}, ctx);
	assert.deepEqual(await stop({}, ctx), first, "a new prompt is asked again");
	await h.before_agent_start[0]({}, ctx);
	assert.equal(await stop({ stop_hook_active: true }, ctx), undefined, "a stop that already answered a stop hook is let go");
}

for (const dir of made) rmSync(dir, { recursive: true, force: true });
console.log("hooks: all tests passed");
