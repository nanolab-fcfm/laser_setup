"""Gets updates from the GitHub repo, and makes a git fetch if
necessary. This is done by checking the latest commit hash on the
remote repository and comparing it to the latest commit hash on the
local repository. If they are different, a pull is made after
user confirmation.
"""
import sys
import logging
try:
    import git
except ImportError:
    sys.exit('Git Python is not installed. Update failed.')

log = logging.getLogger(__name__)


def get_updates(parent=None):
    """Gets updates from the GitHub repo, and makes a git fetch if
    necessary. If parent is given, it's assumed to be a PyQT window
    """
    timeout = 1.
    try:
        repo = git.Repo(search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        log.error("Not a git repository.")
        return

    latest_commit_remote = repo.remotes.origin.fetch(kill_after_timeout=timeout)[0].commit.hexsha
    latest_commit_local = repo.head.commit.hexsha
    common_ancestor = repo.merge_base(latest_commit_local, latest_commit_remote)[0].hexsha
    if latest_commit_remote != common_ancestor:
        if parent is not None:
            reply = parent.question_box(
                'Updates', "New updates are available. Do you want to update?"
            )
            if not reply:
                return

            repo.remotes.origin.pull(kill_after_timeout=timeout)
            file_to_check = 'pyproject.toml'
            diff = repo.git.diff(latest_commit_local, latest_commit_remote, file_to_check)
            if diff:
                log.warning(f"Changes in {file_to_check}. Update the environment.")

        else:
            log.warning("New updates are available. Update with 'git pull'")

    else:
        log.info("No updates available.")


def main(parent=None):
    """Get updates"""
    get_updates(parent=parent)


if __name__ == '__main__':
    main()
