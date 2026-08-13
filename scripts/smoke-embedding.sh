#!/usr/bin/env sh
set -eu

endpoint="${TEI_ENDPOINT:-http://127.0.0.1:8080}"
expected_dimension="${EXPECTED_EMBEDDING_DIMENSION:-2560}"

response="$(
  curl \
    --fail-with-body \
    --silent \
    --show-error \
    --connect-timeout 5 \
    --max-time 120 \
    --header 'Content-Type: application/json' \
    --data '{"inputs":"Magi embedding smoke test"}' \
    "${endpoint}/embed"
)"

printf '%s\n' "${response}" | awk \
  -v expected="${expected_dimension}" \
  -v endpoint="${endpoint}" '
  {
    payload = $0
    gsub(/[[:space:]]/, "", payload)

    if (substr(payload, 1, 2) != "[[" || substr(payload, length(payload) - 1, 2) != "]]" ) {
      print "Smoke test failed: TEI did not return one embedding vector" > "/dev/stderr"
      exit 1
    }

    payload = substr(payload, 3, length(payload) - 4)
    dimension = split(payload, values, ",")
    if (dimension != expected) {
      printf "Smoke test failed: expected dimension %d, got %d\n", expected, dimension > "/dev/stderr"
      exit 1
    }

    number = "^-?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$"
    for (index = 1; index <= dimension; index++) {
      if (values[index] !~ number) {
        printf "Smoke test failed: vector element %d is not finite JSON number\n", index > "/dev/stderr"
        exit 1
      }
    }

    printf "Smoke test passed: endpoint=%s/embed dimension=%d\n", endpoint, dimension
  }
'
