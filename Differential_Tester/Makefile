BUILD=./.bin
DORUST=$(BUILD)/instrument-rust/release/instrument
DOC=$(BUILD)/instrument-c/release/instrument
DOGO=$(BUILD)/instrument-go/instrument
OBJDIR ?= $(BUILD)/verification
N_COUNTER_EXAMPLES=1000
DYLIB=so


build: instrumentor go-instrumentor c-instrumentor
	mkdir $(BUILD)
	cargo build -r --manifest-path instrumentor/Cargo.toml --target-dir $(BUILD)/instrument-rust
	cargo build -r --manifest-path c-instrumentor/Cargo.toml --target-dir $(BUILD)/instrument-c
	go build -C go-instrumentor -o ../$(BUILD)/instrument-go/instrument

clean:
	rm -fr $(BUILD)


go: $(DORUST) $(DOGO)
	$(eval GO_FILE = $(shell find $(TARGET) -name '*.go' | head -n 1))
	mkdir $(OBJDIR)-tmp
	cp $(GO_FILE) $(OBJDIR)-tmp/ground_truth.go
	$(DOGO) $(OBJDIR)-tmp/ground_truth.go
	go fmt $(OBJDIR)-tmp/ground_truth.go
	go build -buildmode c-shared -o $(OBJDIR)-tmp/libground_truth.$(DYLIB) $(OBJDIR)-tmp/ground_truth.go
	$(eval RUST_FILE = $(shell find $(TARGET) -name '*.rs' | head -n 1))
	$(DORUST) -f $(RUST_FILE) -o $(OBJDIR) --arbitrary-precision --capture-stdout --ground-truth $(OBJDIR)-tmp/libground_truth.$(DYLIB) --multi-examples $(N_COUNTER_EXAMPLES)
	mv $(OBJDIR)-tmp/* $(OBJDIR)
	rmdir $(OBJDIR)-tmp

c: $(DORUST) $(DOC)
	$(eval C_FILE = $(shell find $(TARGET) -name '*.json' | head -n 1))
	mkdir $(OBJDIR)-tmp
	$(DOC) -f $(C_FILE) -o $(OBJDIR)-tmp/ground_truth
	cmake -DCMAKE_CXX_COMPILER=gcc10-c++ -S $(OBJDIR)-tmp/ground_truth -B $(OBJDIR)-tmp/ground_truth/_build
	cmake --build $(OBJDIR)-tmp/ground_truth/_build
	$(eval RUST_FILE = $(shell find $(TARGET) -name '*.rs' | head -n 1))
	$(DORUST) -f $(RUST_FILE) -o $(OBJDIR) --arbitrary-precision --capture-stdout --wrapper-structs --ground-truth $(OBJDIR)-tmp/ground_truth/_build/libground_truth.$(DYLIB) --multi-examples $(N_COUNTER_EXAMPLES)
	cp $(OBJDIR)-tmp/ground_truth/_build/libground_truth.$(DYLIB) $(OBJDIR)
	mv $(OBJDIR)-tmp/ground_truth $(OBJDIR)
	rmdir $(OBJDIR)-tmp

clean-obj:
	rm -fr $(OBJDIR)-tmp
	rm -fr $(OBJDIR)

verify: $(OBJDIR)
	LD_LIBRARY_PATH="$(shell readlink -f $(OBJDIR))" \
	RUSTFLAGS="-L $(shell readlink -f $(OBJDIR))" \
	cargo bolero test --manifest-path $(OBJDIR)/Cargo.toml --features fuzzing \
	$(shell LD_LIBRARY_PATH="$(shell readlink -f $(OBJDIR))" \
	RUSTFLAGS="-L $(shell readlink -f $(OBJDIR))" \
	cargo bolero list --manifest-path $(OBJDIR)/Cargo.toml | jq '.test' | head -n 1 | xargs echo) \
	--target-dir $(OBJDIR)/target/__fuzz__  \
	--sanitizer NONE \
	--engine-args="-rss_limit_mb=8096 -max_len=131072" \
	# -e afl --engine-args="-t 300"
	# -e afl --engine-args="-t 2000+" \
	# --corpus-dir $(OBJDIR)/../../examples/url_parse/corpus \

cov: export OBJDIR = $(OBJDIR)
cov: $(OBJDIR)
	./cov.sh

clean-cov: $(OBJDIR)
	rm -rf $(OBJDIR)/*.profraw

.PHONY: clean clean-obj
