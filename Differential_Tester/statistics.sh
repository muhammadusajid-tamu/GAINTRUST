if [ $# -eq 0 ]; then
    echo 'which benchmark?'
    exit 1
fi

echo "Benchmark,Total,Succeeded,Failed"

for bench in "$@"; do
    # fetch latest results folder
    RESULTS=$(echo 2024*$bench | awk '{for (i=1;i<=NF;i++) {print $i}}' | sort | tail -n 1)
    if [ ! -d $RESULTS ]; then
        continue
    fi

    TOTAL=$(ls $RESULTS | wc -l)
    SUCCEEDED=$(find $RESULTS -name "*.show.txt" | wc -l)
    # FAILED=$(find $RESULTS -name "counter_examples.json" | wc -l)
    FAILED=$(find $RESULTS -name "counter_examples.json" -exec sh -c 'jq length "$0"' {} \; | awk '($0!=0) {print}' | wc -l)

    echo "$bench,$TOTAL,$SUCCEEDED,$FAILED"
done

