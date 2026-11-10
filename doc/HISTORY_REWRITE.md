# Commit identity correction

On 10 November 2026, three thesis commits were rewritten to use the project's
established Git identity for both author and committer:
`senqx <89153579+senqx@users.noreply.github.com>`. The repository-local Git
configuration now uses the same identity for future commits.

Only identity headers and the corresponding parent references changed in these
three commits. Their original dates, messages and complete file trees are
preserved. Matching Git tree IDs verify that all source, experimental evidence,
PDFs and archived documents at each checkpoint are byte-identical.

| Original checkpoint ID | Corrected checkpoint |
| --- | --- |
| `71ce10b554028f17c855b6c25562280c7f7ad980` | [80e46d89f7315460b5b9933e84924fa8fec20b92](https://github.com/senqx/Thesis-PIM-ANN/commit/80e46d89f7315460b5b9933e84924fa8fec20b92) |
| `94d3f1d6ba4caea0675b77275ca4f01dfbf313d1` | [1ce1904ce97f7413241e57667bc83d581a3be580](https://github.com/senqx/Thesis-PIM-ANN/commit/1ce1904ce97f7413241e57667bc83d581a3be580) |
| `c36af7b406cb9da885c66080e75269980df7bb0c` | [74b1e0f98c0d44a4201d1aaffd7486289eaebcbc](https://github.com/senqx/Thesis-PIM-ANN/commit/74b1e0f98c0d44a4201d1aaffd7486289eaebcbc) |

Use the corrected IDs for checkout and reproduction. Historical design notes,
archived documents and hashed evidence records retain their original checkpoint
IDs; this table translates those references without changing their contents or
invalidating their recorded file hashes. Earlier commits are unchanged.

The subsequent documentation commit adds this translation and links to it, and
updates the maintained source manifest and generated provenance. It introduces
no new experiment or numerical result. The successful validation of the last
checkpoint's identical file tree is retained in
[GitHub Actions run 42798240902](https://github.com/senqx/Thesis-PIM-ANN/actions/runs/42798240902).
