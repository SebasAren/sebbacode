"""Provides conventional commit message generation following conventionalcommits.org spec.

Format: <type>[optional scope]: <description>

[optional body]

[optional footer(s)]
"""

from dataclasses import dataclass, field


# Standard commit types per conventionalcommits.org
COMMIT_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)


@dataclass
class ConventionalCommit:
    """Builder for conventional commit messages.

    Usage:
        commit = (
            ConventionalCommit()
            .with_type("feat")
            .with_scope("auth")
            .with_description("add OAuth2 support")
            .with_body("Added support for Google and GitHub OAuth2 providers.")
            .with_footer("Closes #123")
        )
        print(commit.build())
    """

    _type: str = field(default="", repr=False)
    _scope: str = field(default="", repr=False)
    _description: str = field(default="", repr=False)
    _body: str = field(default="", repr=False)
    _footers: list[str] = field(default_factory=list, repr=False)
    _breaking: bool = field(default=False, repr=False)

    def with_type(self, commit_type: str) -> "ConventionalCommit":
        """Set the commit type (e.g., feat, fix, docs).

        Raises:
            ValueError: If commit_type is not in COMMIT_TYPES.
        """
        if commit_type not in COMMIT_TYPES:
            raise ValueError(
                f"Unknown commit type '{commit_type}'. "
                f"Must be one of: {', '.join(COMMIT_TYPES)}"
            )
        self._type = commit_type
        return self

    def with_scope(self, scope: str) -> "ConventionalCommit":
        """Set the optional scope (e.g., api, ui, auth)."""
        self._scope = scope
        return self

    def with_description(self, description: str) -> "ConventionalCommit":
        """Set the commit description (required)."""
        self._description = description
        return self

    def with_body(self, body: str) -> "ConventionalCommit":
        """Set the commit body (optional, can be multi-line)."""
        self._body = body
        return self

    def with_footer(self, footer: str) -> "ConventionalCommit":
        """Add a footer line (can be called multiple times)."""
        self._footers.append(footer)
        return self

    def with_breaking(self, breaking: bool = True) -> "ConventionalCommit":
        """Mark this commit as a breaking change."""
        self._breaking = breaking
        return self

    def _format_header(self) -> str:
        """Format the commit header: type[scope]: description [!]"""
        if not self._type:
            raise ValueError("Commit type is required")
        if not self._description:
            raise ValueError("Commit description is required")

        header = f"{self._type}"
        if self._scope:
            header += f"({self._scope})"
        if self._breaking:
            header += "!"
        header += f": {self._description}"
        return header

    def build(self) -> str:
        """Build and return the complete conventional commit message."""
        parts = [self._format_header()]

        if self._body:
            parts.append(self._body)

        if self._footers:
            parts.append("\n".join(self._footers))

        return "\n\n".join(parts)


def make_commit(
    commit_type: str,
    description: str,
    scope: str = "",
    body: str = "",
    footers: list[str] | None = None,
    breaking: bool = False,
) -> str:
    """Create a conventional commit message in one call.

    Args:
        commit_type: Commit type (e.g., feat, fix, docs)
        description: Brief description of the change
        scope: Optional scope (e.g., api, ui)
        body: Optional detailed body text
        footers: Optional list of footer lines
        breaking: Whether this is a breaking change

    Returns:
        A properly formatted conventional commit message string

    Raises:
        ValueError: If type or description is empty
    """
    commit = (
        ConventionalCommit()
        .with_type(commit_type)
        .with_scope(scope)
        .with_description(description)
        .with_body(body)
        .with_breaking(breaking)
    )
    for footer in footers or []:
        commit.with_footer(footer)
    return commit.build()
