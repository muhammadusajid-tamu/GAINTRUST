
RUSTFLAGS="-C instrument-coverage" cargo test --manifest-path $OBJDIR/Cargo.toml


LLVM_COV=$(find $(rustc --print sysroot) -name "llvm-cov" | head -n 1)
LLVM_PROFDATA=$(find $(rustc --print sysroot) -name "llvm-profdata" | head -n 1)
TEST_BIN=$(find $OBJDIR/target/debug/deps -type f -name "verification-*" ! -name "*.*")

$LLVM_PROFDATA merge -sparse $OBJDIR/*.profraw -o $OBJDIR/cov.profdata
$LLVM_COV report -instr-profile=$OBJDIR/cov.profdata $TEST_BIN
