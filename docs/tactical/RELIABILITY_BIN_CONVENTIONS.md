# Reliability-bin numerical conventions

Log loss and Brier scores use saved probabilities under each task's explicit
clipping and Brier definitions. Reliability diagrams add a separate grouping
choice; binning does not affect fitted coefficients or the designated loss
comparisons.

An independent pre-evaluation review noted that `numpy.linspace(0, 1, 11)` can
store nominal edges such as 0.3 as 0.30000000000000004. At an exactly representable
input float written as `0.3`, `searchsorted` therefore assigns the earlier bin.
The already frozen NFL and MCP tennis implementations retain their **exact
serialized floating-point edges**, rather than silently changing numerical
reporting after development. Display labels may be rounded, but the stored edge
and closure convention are authoritative. Values microscopically close to a
nominal decimal boundary can differ from an ideal decimal-arithmetic diagram.

The baseball pitch-sequence implementation was still unbound when this was
identified; its reviewed local reporting path uses explicit `arange(11)/10`
edges and tests nominal decimal endpoints. Soccer and ACB use their separately
listed fixed edge arrays. These conventions should not be treated as evidence
that one sport's calibration is superior to another's.

All reports preserve empty-bin counts, support and raw probabilities. A visually
close diagonal, one ECE number or a favorable log loss does not alone establish
calibration. Small groups, annotation uncertainty and population change remain
separate limitations. Any later binning sensitivity should reuse the same saved
probabilities, carry a separate reporting label and never alter model selection.
