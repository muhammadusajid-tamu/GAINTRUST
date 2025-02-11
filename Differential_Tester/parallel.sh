BENCHMARKS=$(pwd)/benchmarks/$1
if [ $(find $BENCHMARKS -name "*.go" | wc -l) -gt 0 ]; then
    LANGUAGE=go
elif [ $(find $BENCHMARKS -name "*.json" | wc -l) -gt 0 ]; then
    LANGUAGE=c
else
    echo 'what language are you trying?'
    exit 1
fi

WORKSPACE=$(pwd)/.bin
LLVM_COV=$(find $(rustc --print sysroot) -name "llvm-cov" | head -n 1)
LLVM_PROFDATA=$(find $(rustc --print sysroot) -name "llvm-profdata" | head -n 1)

RESULTS=$(pwd)/$1-results
mkdir $RESULTS

instrument() {
    bench=$1
    echo "instrumenting $bench.."
    OBJDIR=$WORKSPACE/$bench
    OBJDIR=$OBJDIR make $LANGUAGE TARGET=$BENCHMARKS/$bench 2> /dev/null
}

verify() {
    bench=$1
    mkdir $RESULTS/$bench
    OBJDIR=$WORKSPACE/$bench
    if [ -d $OBJDIR ]; then
        echo "start verifying $bench.."
        OBJDIR=$OBJDIR make verify > $RESULTS/$bench/$bench.log 2>&1
        PE=$(grep 'positive examples: ' $RESULTS/$bench/$bench.log)
        CE=$(grep 'counter examples: ' $RESULTS/$bench/$bench.log)
        if [ $? -eq 0 ]; then
            prefix='counter examples: '
            echo $CE | sed -e "s/^$prefix//" > $RESULTS/$bench/counter_examples.json
            prefix='positive examples: '
            echo $PE | sed -e "s/^$prefix//" > $RESULTS/$bench/positive_examples.json
            
            if [ $(jq length $RESULTS/$bench/counter_examples.json) -eq 0 ]; then
                echo "$bench verified"
                # RUSTFLAGS="-C instrument-coverage" \
                RUSTFLAGS="-Zunstable-options -C instrument-coverage=except-unused-functions" \
                cargo test --manifest-path $OBJDIR/Cargo.toml 2> /dev/null
                TEST_BIN=$(find $OBJDIR/target/debug/deps -type f -name "verification-*" ! -name "*.*")
                $LLVM_PROFDATA merge -sparse $OBJDIR/*.profraw -o $OBJDIR/cov.profdata
                $LLVM_COV report -instr-profile=$OBJDIR/cov.profdata $TEST_BIN > $RESULTS/$bench/$bench.report.txt
                $LLVM_COV show -instr-profile=$OBJDIR/cov.profdata $TEST_BIN \
                --show-instantiations --show-line-counts-or-regions > $RESULTS/$bench/$bench.show.txt
            fi

            cargo clean --manifest-path $OBJDIR/Cargo.toml 2> /dev/null
            if [ -d $OBJDIR/src/__fuzz__ ]; then
                rm -r $OBJDIR/src/__fuzz__
            fi
            mv $OBJDIR $RESULTS/$bench/replay
        fi

    fi
    OBJDIR=$OBJDIR make clean-obj
    echo "$bench finished."
}

BATCH_SIZE=32
for bench in $(ls $BENCHMARKS); do
    instrument $bench &

    # allow to execute up to $N jobs in parallel
    if [[ $(jobs -r -p | wc -l) -ge $BATCH_SIZE ]]; then
        # now there are $N jobs already running, so wait here for any job
        # to be finished so there is a place to start next one.
        wait
    fi
done

wait

BATCH_SIZE=64
for bench in $(ls $BENCHMARKS); do
    verify $bench &

    # allow to execute up to $N jobs in parallel
    if [[ $(jobs -r -p | wc -l) -ge $BATCH_SIZE ]]; then
        # now there are $N jobs already running, so wait here for any job
        # to be finished so there is a place to start next one.
        wait
    fi
done

wait

mv $RESULTS $(pwd)/$(date +%Y-%m-%d_%H-%M)-$1
