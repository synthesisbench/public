#!/usr/bin/env bash
# Prove the floor suites still discriminate.
#
# A rewritten synthetic fixture can pass every test while landing on a different
# grader branch than the real fixture did — the assertion gets adjusted to match
# and the floor quietly stops being pinned. Green tests do not prove that.
#
# So: break the grader on purpose, one constant at a time, and require the named
# floor tests to go red. A mutation that nothing catches is a floor nobody guards.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

run_pytest() {
  # $1 = task dir under the mutated tree, rest = pytest args
  local task_dir=$1
  shift
  uv run --frozen python -m pytest \
    "$work/tasks/$task_dir/tests" -q -p no:cacheprovider "$@" 2>&1
}

failures=0

# Each mutation: task | sed program applied to grade.py | test that MUST go red
mutate() {
  local label=$1 task=$2 sed_prog=$3 guard_test=$4

  rm -rf "$work/tasks"
  cp -R "$repo_root/tasks" "$work/tasks"

  local grader="$work/tasks/$task/tests/grade.py"
  local before
  before=$(shasum <"$grader" | cut -d' ' -f1)
  sed -i.bak -E "$sed_prog" "$grader"
  rm -f "$grader.bak"
  local after
  after=$(shasum <"$grader" | cut -d' ' -f1)

  if [[ $before == "$after" ]]; then
    echo "FAIL [$label]: mutation was a no-op — the sed program matched nothing."
    failures=$((failures + 1))
    return
  fi

  if run_pytest "$task" -k "$guard_test" >"$work/out.txt" 2>&1; then
    echo "FAIL [$label]: '$guard_test' still PASSED against a broken grader."
    echo "       The fixture no longer exercises the branch it claims to pin."
    failures=$((failures + 1))
  else
    echo "PASS [$label]: '$guard_test' went red, as it must."
  fi
}

echo "== Mutating graders; the named floor tests must fail =="

# Emitting nothing must score 0. Replace recall with a constant participation
# prize and the extract-nothing assertion has to catch it. Under the F1 reward
# a constant recall also drags precision's empty-input default up with it, so
# extract-nothing scores a full 1.0 rather than merely drifting off zero.
mutate "extraction/emit-nothing-floor" full_text_extraction \
  's|^    recall = tp / .*$|    recall = 1.0|' \
  'test_degenerate_baselines_bounded'

# Widen the ratio tolerance until a wrong pooled estimate counts as "within tolerance".
# The oracle would still pass (it replays gold exactly); only a test that pins a WRONG
# number as wrong can catch this.
mutate "meta/log-tolerance" meta_analysis \
  's/^    log_abs: float = 0\.05.*$/    log_abs: float = 1000.0/' \
  'test_same_conclusion_wrong_numbers_misses_ci_reward'

# Difference measures (Mean Difference) are graded on a relative tolerance, not the
# log-space one. Widen it and a wrong mean difference has to stop reading as wrong.
mutate "meta/rel-tolerance" meta_analysis \
  's/^    rel: float = 0\.05.*$/    rel: float = 1000.0/' \
  'test_non_significant_gold_does_not_require_direction'

# Majority-class guessing must score 0. Replace kappa's chance correction with raw
# accuracy and all-low guessing starts scoring well above zero.
mutate "rob/kappa-chance-correction" risk_of_bias \
  's/expected_disagreement = 0$/expected_disagreement = total * 1000000/' \
  'test_all_low_predictions_score_zero_like_missing_defaults'

# Constant screening policies must remain chance-level. Bypass the observed vs.
# expected disagreement comparison and the degenerate floor test must fail.
mutate "screening/chance-correction" full_text_screening \
  's/^    return max.*observed_cost.*$/    return 1.0/' \
  'test_degenerate_baselines_bounded'

# Title/abstract screening carries the same chance correction over a far more
# skewed pool, where a class-prevalence floor would be worth the most.
mutate "title-abstract/chance-correction" title_abstract_screening \
  's/^    return max.*observed_cost.*$/    return 1.0/' \
  'test_degenerate_baselines_bounded'

# Missing an eligible study costs ten times a spurious include — that asymmetry
# is the whole point of the reward. Flatten it and the ordering test must fail.
mutate "title-abstract/false-negative-cost" title_abstract_screening \
  's/^FALSE_NEGATIVE_COST = 10.0$/FALSE_NEGATIVE_COST = 1.0/' \
  'test_false_negative_costs_more_than_false_positive'

echo
if ((failures)); then
  echo "$failures mutation(s) survived. The floors are not pinned."
  exit 1
fi
echo "All mutations were caught. The floor suites discriminate."
