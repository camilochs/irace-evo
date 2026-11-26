#!/bin/bash
# Checks the example's target runner on its own, in a scratch copy: whatever
# happens to the program, irace must get exactly one number on standard
# output and nothing on standard error (irace reads both and stops on
# anything else). Cases: the original, a variant whose program is missing,
# a variant that loops forever, a variant that crashes.
#   tests/evo/runner-test.sh
set -u
here="$(cd "$(dirname "$0")" && pwd)"
work=$(mktemp -d)
cp -R "$here/../../examples/tsp-ga-evolution/src" "$here/../../examples/tsp-ga-evolution/target-runner" \
      "$here/../../examples/tsp-ga-evolution/tuning_instances" "$work/"
cd "$work"
mkdir -p bin
printf '#!/bin/bash\nwhile :; do :; done\n' > bin/loops; chmod +x bin/loops
printf '#!/bin/bash\nkill -SEGV $$\n' > bin/crashes; chmod +x bin/crashes
printf 'config_id,executable_path,variant_id\n2,"%s/bin/missing","v_missing"\n3,"%s/bin/loops","v_loops"\n4,"%s/bin/crashes","v_crashes"\n' "$work" "$work" "$work" > .irace_evo_variants.csv
fails=0
run() {  # config_id, expected stdout, expected reason in the log ('' for none), description
  : > target-runner.log
  out=$(TIME_LIMIT=1 ./target-runner "$1" 1 1 tuning_instances/len_100_sigma2_0.txt -p 50 -pe 0.2 -pm 0.2 -rhoe 0.6 2> err.txt)
  lines=$(printf '%s\n' "$out" | grep -c .)
  reason=$(cat target-runner.log)
  if [ "$lines" -eq 1 ] && [[ "$out" =~ $2 ]] && [ ! -s err.txt ] \
     && { [ -z "$3" ] && [ -z "$reason" ] || [ -n "$3" ] && [[ "$reason" == *"$3"* ]]; }; then
    echo "PASS $4 :: stdout '$out', stderr empty${reason:+, log: ${reason#*: }}"
  else
    echo "FAIL $4 :: stdout '$out', stderr '$(head -c 200 err.txt)', log '$reason'"; fails=$((fails + 1))
  fi
}
run 1 '^-[0-9]+(\.[0-9]+)?$' "" "the original prints its negative score"
run 2 '^999999$' "which is missing" "a missing variant gets the penalty"
start=$SECONDS
run 3 '^999999$' "s of CPU" "a variant that loops forever is stopped at the CPU limit"
echo "     (after $((SECONDS - start)) s of wall time; the CPU limit is 12 s)"
run 4 '^999999$' "signal 11" "a variant that crashes gets the penalty"
exit $fails
