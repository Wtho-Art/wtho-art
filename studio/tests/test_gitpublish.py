from pathlib import Path

import gitpublish


def test_allowed_paths():
    assert gitpublish.is_allowed("data/works.json")
    assert gitpublish.is_allowed("works/touched/touched.jpg")
    assert gitpublish.is_allowed("works/new/index.html")
    assert gitpublish.is_allowed("images/portrait.jpg")
    assert gitpublish.is_allowed("images/portrait/index.html")
    assert gitpublish.is_allowed("images/portrait/portrait-2.jpg")
    assert gitpublish.is_allowed("sitemap.xml")
    assert gitpublish.is_allowed(".gitignore")
    assert not gitpublish.is_allowed("studio/app.py")
    assert not gitpublish.is_allowed("originals/a.jpg")
    assert not gitpublish.is_allowed("works/../../data/site.json")
    assert not gitpublish.is_allowed("index.html")
    assert not gitpublish.is_allowed("works/a/file.tif")
    assert not gitpublish.is_allowed("images/evil.php")
    assert not gitpublish.is_allowed("images/portrait/notes.txt")


def test_directory_expands_to_safe_files_only(tmp_path):
    folder = tmp_path / "works" / "blue"
    folder.mkdir(parents=True)
    (folder / "index.html").write_text("x", encoding="utf-8")
    (folder / "blue.jpg").write_bytes(b"jpg")
    (folder / "notes.txt").write_text("no", encoding="utf-8")
    allowed, blocked = gitpublish.files_to_commit(tmp_path, "?? works/blue/\n M index.html\n")
    assert allowed == ["works/blue/blue.jpg", "works/blue/index.html"]
    assert "index.html" in blocked
    assert "works/blue/notes.txt" in blocked
    images = tmp_path / "images" / "portrait"
    images.mkdir(parents=True)
    (images / "index.html").write_text("page", encoding="utf-8")
    (images / "portrait.jpg").write_bytes(b"jpg")
    (images / "notes.txt").write_text("no", encoding="utf-8")
    allowed, blocked = gitpublish.files_to_commit(tmp_path, "?? images/portrait/\n")
    assert allowed == ["images/portrait/index.html", "images/portrait/portrait.jpg"]
    assert blocked == ["images/portrait/notes.txt"]


def test_ssh_success_ignores_github_exit_status():
    ok, message = gitpublish.ssh_result(0, "Hi Wtho-Art! You've successfully authenticated, but GitHub does not provide shell access.")
    assert ok
    assert gitpublish.github_account(message) == "Wtho-Art"
    ok, _message = gitpublish.ssh_result(1, "successfully authenticated")
    assert not ok


def test_publish_push_has_no_force_and_skips_blocked(tmp_path):
    calls = []
    state = {"resets": 0}

    def runner(args, root):
        calls.append(list(args))
        if args[1] == "status":
            return " M data/site.json\n M index.html\n?? studio/app.py\n"
        if args[1] == "reset":
            state["resets"] += 1
            return ""
        if args[:3] == ["git", "diff", "--cached"]:
            if state["resets"]:
                return "data/site.json\n"
            return "data/site.json\nindex.html\n"
        return ""

    result = gitpublish.publish(tmp_path, "Add a line", runner=runner, ssh_ok=True)
    assert result["committed"] == ["data/site.json"]
    assert "index.html" in result["blocked"]
    assert ["git", "pull", "--ff-only", "origin", "main"] in calls
    assert ["git", "push", "origin", "main"] in calls
    assert not any("--force" in arg or arg == "-f" for command in calls for arg in command)
    assert state["resets"] == 1


def test_publish_stops_when_pull_fails(tmp_path):
    calls = []

    def runner(args, root):
        calls.append(args[1])
        if args[1] == "status":
            return " M data/site.json\n"
        if args[1] == "pull":
            raise gitpublish.GitError("fast-forward nicht möglich")
        return ""

    try:
        gitpublish.publish(tmp_path, "Update", runner=runner, ssh_ok=True)
    except gitpublish.GitError as exc:
        assert "fast-forward" in str(exc)
    else:
        raise AssertionError("pull failure was ignored")
    assert "commit" not in calls
    assert "push" not in calls


def test_publish_requires_ssh_and_a_one_line_message(tmp_path):
    def runner(args, root):
        raise AssertionError("git should not run")

    try:
        gitpublish.publish(tmp_path, "Hi", runner=runner, ssh_ok=False)
    except gitpublish.GitError:
        pass
    else:
        raise AssertionError("missing key was ignored")
    try:
        gitpublish.validate_message("two\nlines")
    except gitpublish.GitError:
        pass
    else:
        raise AssertionError("newline was accepted")
