#!/usr/bin/env python3
"""
install_ai_skills.py - put the first-party skills into every AI app on this machine, and
update the plugins and extensions the apps already have. Safe to run again and again:
what is current is skipped, what changed is updated, nothing is ever deleted.

    python3 install_ai_skills.py              # do it
    python3 install_ai_skills.py --dry-run    # say what it would do
    python3 install_ai_skills.py --no-apps    # skills only, no plugin or extension updates
    python3 install_ai_skills.py --claude     # also link into ~/.claude/skills (see below)
    python3 install_ai_skills.py --selftest

WHICH SKILLS. Two kinds:
  - first-party: every SKILL.md folder under skills/ or tools/skills/ in this repo and in each
    git repo beside it. Every app gets them.
  - vendored plugins, per app: plugins-other-apps.tsv says which plugin goes to which app. The
    app gets the plugin's skills as plain skills - the same folders Claude loads (the marketplace
    entry's list, else plugin.json's, else the plugin's skills/ folder). Its commands, agents and
    hooks do not port. Claude keeps the marketplace route for plugins. The list stays short:
    378 skill descriptions would fill an app's context before any work.

WHERE, per app (each target is used only when the app is on this machine):
    Gemini CLI    ~/.agents/skills   the shared folder; Gemini CLI reads it (2026-10-01)
    Qwen Code     ~/.qwen/skills     read by Qwen Code; it has no `skills` command
    Codex         ~/.codex/skills    only when ~/.codex exists; Codex loads SKILL.md folders
                                     there (seen 2026-10-01). build-codex.sh --install adds
                                     the plugin commands as prompts
    Claude Code   ~/.claude/skills   only with --claude. Claude gets these skills from the
                                     marketplaces and the claude.ai account already, and a
                                     skill loaded twice shows twice.

HOW. A LINK to the repo folder (a symlink; a junction on Windows when symlinks need admin),
so `git pull` is the update and nothing is copied twice. Where no link can be made, a copy
with a .bso-skill-source stamp; a copy whose source changed is replaced, the old one moved
to <target>/../skills-before/<name>-<date>, never deleted. A folder of the same name that
this script did not make (another installer's copy) is left alone and reported.

APPS. For what each app already has installed, its own update command runs:
    claude plugin marketplace update + claude plugin update <each installed plugin>
    gemini extensions update --all
    qwen extensions update --all
The Claude desktop app keeps its own plugins and updates them itself; its command line on
this Mac showed none installed on 2026-10-01.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STAMP = ".bso-skill-source"
PLAN = os.path.join(HERE, "plugins-other-apps.tsv")


# ------------------------------------------------------------------ what to install
def skills(repos):
    """{name: folder} for every first-party SKILL.md folder; the first repo wins a name."""
    found, clash = {}, []
    for repo in repos:
        for sub in ("skills", os.path.join("tools", "skills")):
            base = os.path.join(repo, sub)
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                d = os.path.join(base, name)
                if os.path.isfile(os.path.join(d, "SKILL.md")):
                    if name in found:
                        clash.append((name, d))
                    else:
                        found[name] = d
    return found, clash


def plugin_skills(repo, entry):
    """The SKILL.md folders a Claude plugin entry loads, in Claude's own order: the marketplace
    entry's "skills" list, else plugin.json's, else every folder in the plugin's skills/."""
    src = entry.get("source")
    if not isinstance(src, str):
        return []                                       # a plugin fetched from elsewhere: not vendored
    src = os.path.normpath(os.path.join(repo, src))
    rel = entry.get("skills")
    if not rel:
        try:
            with open(os.path.join(src, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
                rel = json.load(fh).get("skills")
        except (OSError, ValueError):
            rel = None
    if rel:
        dirs = [os.path.normpath(os.path.join(src, r)) for r in rel]
    else:
        base = os.path.join(src, "skills")
        dirs = [os.path.join(base, d) for d in sorted(os.listdir(base))] if os.path.isdir(base) else []
    return [d for d in dirs if os.path.isfile(os.path.join(d, "SKILL.md"))]


def plan(repo=REPO, path=PLAN):
    """{app: {skill name: folder}}: the vendored plugins' skills each app gets."""
    try:
        with open(path, encoding="utf-8") as fh:
            rows = [ln.rstrip("\r\n").split("\t") for ln in fh if ln.strip() and not ln.startswith("#")]
        with open(os.path.join(repo, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
            market = {p["name"]: p for p in json.load(fh)["plugins"]}
    except (OSError, ValueError, KeyError):
        return {}
    if not rows:
        return {}
    apps, out = rows[0][1:], {a: {} for a in rows[0][1:]}
    for r in rows[1:]:
        if r[0] not in market:
            print("  ! %s is in %s but not in marketplace.json - skipped" % (r[0], os.path.basename(path)))
            continue
        dirs = plugin_skills(repo, market[r[0]])
        for app, val in zip(apps, r[1:]):
            if val.strip().lower() == "yes":
                for d in dirs:
                    out[app].setdefault(os.path.basename(d), d)
    return out


def ours_not_listed(folder, wanted, root):
    """Links in an app's folder that this installer made (they point into the repos) but that
    no list asks for any more. Reported, never removed."""
    if not os.path.isdir(folder):
        return []
    root, here = os.path.realpath(root), os.path.realpath(folder)   # macOS: /var is /private/var
    out = []
    for n in os.listdir(folder):
        real = os.path.realpath(os.path.join(folder, n))
        if n not in wanted and real != os.path.join(here, n) and real.startswith(root + os.sep):
            out.append(n)
    return sorted(out)


def repos_beside(repo=REPO):
    """This repo first, then every git repo in the same folder."""
    parent = os.path.dirname(repo)
    out = [repo]
    for n in sorted(os.listdir(parent)):
        p = os.path.join(parent, n)
        if p != repo and os.path.isdir(os.path.join(p, ".git")):
            out.append(p)
    return out


def targets(home, want_claude=False):
    """[(app, folder)] for the apps on this machine."""
    out = []
    if shutil.which("gemini") or os.path.isdir(os.path.join(home, ".agents")):
        out.append(("gemini-cli", os.path.join(home, ".agents", "skills")))
    if shutil.which("qwen") or os.path.isdir(os.path.join(home, ".qwen")):
        out.append(("qwen-code", os.path.join(home, ".qwen", "skills")))
    if os.path.isdir(os.path.join(home, ".codex")):
        out.append(("codex", os.path.join(home, ".codex", "skills")))
    if want_claude:
        out.append(("claude-code", os.path.join(home, ".claude", "skills")))
    return out


# ------------------------------------------------------------------ one skill, one app
def tree_hash(folder):
    h = hashlib.sha1()
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for f in sorted(files):
            if f == STAMP or f == ".DS_Store":
                continue
            p = os.path.join(root, f)
            h.update(os.path.relpath(p, folder).replace(os.sep, "/").encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


def link(src, dst):
    """A link to src at dst: a symlink, else (Windows) a junction, else False."""
    try:
        os.symlink(src, dst, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", dst, src], capture_output=True, text=True)
        return r.returncode == 0
    return False


def copy(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".DS_Store"))
    with open(os.path.join(dst, STAMP), "w", encoding="utf-8") as fh:
        json.dump({"source": src, "hash": tree_hash(src)}, fh)


def place(name, src, folder, dry=False):
    """Install or update one skill in one app's folder. Returns what happened."""
    dst = os.path.join(folder, name)
    if os.path.realpath(dst) == os.path.realpath(src):
        return "current"                                  # our link: git pull keeps it current
    if os.path.lexists(dst):
        try:
            with open(os.path.join(dst, STAMP), encoding="utf-8") as fh:
                stamp = json.load(fh)
        except (OSError, ValueError):
            return "not ours"                             # another installer's copy: leave it
        if os.path.realpath(stamp.get("source", "")) != os.path.realpath(src):
            return "not ours"
        if stamp.get("hash") == tree_hash(src):
            return "current"
        if dry:
            return "would update"
        before = os.path.join(os.path.dirname(folder), "skills-before")
        os.makedirs(before, exist_ok=True)
        keep = os.path.join(before, "%s-%s" % (name, datetime.date.today().isoformat()))
        n = 2
        while os.path.lexists(keep):
            keep = os.path.join(before, "%s-%s-%d" % (name, datetime.date.today().isoformat(), n))
            n += 1
        shutil.move(dst, keep)                            # moved aside, never deleted
        (link(src, dst) or copy(src, dst))
        return "updated"
    if dry:
        return "would install"
    os.makedirs(folder, exist_ok=True)
    if link(src, dst):
        return "linked"
    copy(src, dst)
    return "copied"


# ------------------------------------------------------------------ the apps' own updates
def run(cmd, dry, timeout=600):
    print("   $ " + " ".join(cmd))
    if dry:
        return ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        tail = (r.stdout + r.stderr).strip().splitlines()[-2:]
        for ln in tail:
            print("     " + ln[:160])
        return r.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        print("     ! %s" % e)
        return ""


def update_apps(dry):
    """Update what each app already has. Nothing new is installed here."""
    if shutil.which("claude"):
        print("\n== Claude Code (command line) ==")
        run(["claude", "plugin", "marketplace", "update"], dry)
        try:
            listed = json.loads(run(["claude", "plugin", "list", "--json"], False) or "[]")
        except ValueError:
            listed = []
        items = listed.get("installed", []) if isinstance(listed, dict) else listed
        # ponytail: the entry shape is not seen yet (none installed on 2026-10-01); id, or name@marketplace
        ids = [i if isinstance(i, str) else i.get("id") or "%s@%s" % (i.get("name"), i.get("marketplace"))
               for i in items]
        for pid in ids:
            run(["claude", "plugin", "update", pid], dry)
        if not ids:
            print("   no plugin installed for the command line (the desktop app updates its own)")
    for app in ("gemini", "qwen"):
        if shutil.which(app):
            print("\n== %s extensions ==" % app)
            run([app, "extensions", "update", "--all"], dry)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Install first-party skills into every AI app, and update what the apps have.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-apps", action="store_true", help="skills only: no plugin or extension updates")
    ap.add_argument("--claude", action="store_true", help="also link into ~/.claude/skills")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    found, clash = skills(repos_beside())
    per_app = plan()
    tg = targets(os.path.expanduser("~"), a.claude)
    print("%d first-party skills: %s" % (len(found), ", ".join(sorted(found))))
    for name, d in clash:
        print("  ! %s also in %s - the first one found is used" % (name, d))
    if not tg:
        print("No AI app with a skills folder found on this machine.")
    tally, root = {}, os.path.dirname(REPO)
    for app, folder in tg:
        wanted = dict(found)                            # first-party first: it wins a name
        for name, d in per_app.get(app, {}).items():
            wanted.setdefault(name, d)
        print("\n== %s  (%s): %d first-party + %d from plugins ==" % (app, folder, len(found), len(wanted) - len(found)))
        for name, src in sorted(wanted.items()):
            what = place(name, src, folder, a.dry_run)
            tally[what] = tally.get(what, 0) + 1
            if what != "current":
                print("  %-14s %s" % (what, name))
        for name in ours_not_listed(folder, wanted, root):
            print("  %-14s %s  (remove the link by hand if it should go)" % ("not listed", name))
    print("\nSkills: " + ", ".join("%d %s" % (n, k) for k, n in sorted(tally.items())) if tally else "")
    if tally.get("not ours"):
        print("'not ours' = a folder of that name made by something else. Left alone: remove it by hand, then run again.")
    if not a.no_apps:
        update_apps(a.dry_run)
    print("\nRestart each AI app to load new skills.")


def selftest():
    tmp = tempfile.mkdtemp(prefix="ai-skills-test-")
    try:
        repo = os.path.join(tmp, "repo")
        src = os.path.join(repo, "skills", "alpha")
        os.makedirs(src)
        with open(os.path.join(src, "SKILL.md"), "w") as fh:
            fh.write("---\nname: alpha\n---\nv1\n")
        found, _ = skills([repo])
        assert found == {"alpha": src}, found
        folder = os.path.join(tmp, "home", ".agents", "skills")
        assert place("alpha", src, folder, dry=True) == "would install"
        first = place("alpha", src, folder)
        assert first in ("linked", "copied"), first
        assert place("alpha", src, folder) == "current", "a second run must skip"
        with open(os.path.join(src, "SKILL.md"), "a") as fh:
            fh.write("v2\n")
        second = place("alpha", src, folder)
        assert second == ("current" if first == "linked" else "updated"), second   # a link follows the source
        # a copy made by someone else is never touched
        other = os.path.join(folder, "beta")
        os.makedirs(other)
        assert place("beta", src, folder) == "not ours" and os.path.isdir(other)
        # the copy route: stamp, skip when unchanged, move the old copy aside when changed
        cfolder = os.path.join(tmp, "copies")
        os.makedirs(cfolder)
        copy(src, os.path.join(cfolder, "alpha"))
        assert place("alpha", src, cfolder) == "current"
        with open(os.path.join(src, "SKILL.md"), "a") as fh:
            fh.write("v3\n")
        assert place("alpha", src, cfolder) == "updated"
        kept = os.listdir(os.path.join(tmp, "skills-before"))
        assert len(kept) == 1 and kept[0].startswith("alpha-"), kept
        # a plugin's skills, per app, from the list and the marketplace
        os.makedirs(os.path.join(repo, ".claude-plugin"))
        plug = os.path.join(repo, "plugins", "p1")
        for sk in ("one", "two"):
            os.makedirs(os.path.join(plug, "skills", sk))
            open(os.path.join(plug, "skills", sk, "SKILL.md"), "w").close()
        with open(os.path.join(repo, ".claude-plugin", "marketplace.json"), "w") as fh:
            json.dump({"plugins": [{"name": "p1", "source": "./plugins/p1"},
                                   {"name": "p2", "source": "./", "skills": ["./skills/alpha"]}]}, fh)
        tsv = os.path.join(tmp, "list.tsv")
        with open(tsv, "w") as fh:
            fh.write("# comment\nplugin\tgemini-cli\tcodex\np1\tyes\tno\np2\tno\tyes\nmissing\tyes\tyes\n")
        got = plan(repo, tsv)
        assert sorted(got["gemini-cli"]) == ["one", "two"] and list(got["codex"]) == ["alpha"], got
        assert ours_not_listed(folder, {}, tmp) == ["alpha"], "a link of ours no list asks for is reported"
        print("install_ai_skills selftest ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
