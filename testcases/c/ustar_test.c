#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "uastar.h"  // Assumes this header declares struct path_finder and all functions

// For these tests, we assume a grid size of 5x5.
#define GRID_ROWS 5
#define GRID_COLS 5
#define TOTAL_CELLS (GRID_ROWS * GRID_COLS)

// Dummy fill functions:
int always_passable(struct path_finder *pf, int32_t col, int32_t row) {
    (void)pf; (void)col; (void)row;
    return 1;
}

int never_passable(struct path_finder *pf, int32_t col, int32_t row) {
    (void)pf; (void)col; (void)row;
    return 0;
}

// Dummy score function that returns zero cost.
int zero_score(struct path_finder *pf, int32_t col, int32_t row, void *data) {
    (void)pf; (void)col; (void)row; (void)data;
    return 0;
}

// ----------------------------------------------------------------------
// Test the heuristic function (Manhattan distance).
void test_heuristic() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    // Set the end at (4,4)
    pf.end = 4 + 4 * pf.cols;
    // For cell (0,0): distance = 4 + 4 = 8.
    int32_t h = path_finder_heuristic(&pf, 0);
    assert(h == 8);
    // For cell (2,2): distance = |2-4| + |2-4| = 2 + 2 = 4.
    int32_t cell = 2 + 2 * pf.cols;
    h = path_finder_heuristic(&pf, cell);
    assert(h == 4);
    printf("test_heuristic passed.\n");
}

// ----------------------------------------------------------------------
// Test open-set emptiness.
void test_open_set_empty() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    memset(pf.state, 0, sizeof(pf.state));
    // Initially, no cell is marked open.
    assert(path_finder_open_set_is_empty(&pf) == 1);
    // Mark one cell as open.
    pf.state[3] |= PATH_FINDER_MASK_OPEN;
    assert(path_finder_open_set_is_empty(&pf) == 0);
    printf("test_open_set_empty passed.\n");
}

// ----------------------------------------------------------------------
// Test selecting the lowest f_score from the open set.
void test_lowest_in_open_set() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    memset(pf.state, 0, sizeof(pf.state));
    // Mark several cells as open and assign different f_scores.
    pf.state[5] |= PATH_FINDER_MASK_OPEN;
    pf.state[10] |= PATH_FINDER_MASK_OPEN;
    pf.state[15] |= PATH_FINDER_MASK_OPEN;
    pf.f_score[5] = 10;
    pf.f_score[10] = 5;  // lowest score here.
    pf.f_score[15] = 20;
    int32_t lowest = path_finder_lowest_in_open_set(&pf);
    assert(lowest == 10);
    printf("test_lowest_in_open_set passed.\n");
}

// ----------------------------------------------------------------------
// Test reconstructing the path via the parent chain.
// Here, we set a simple chain: start=0, then cell 3’s parent = 0, then cell 7’s parent = 3, with end = 7.
void test_reconstruct_path() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    memset(pf.state, 0, sizeof(pf.state));
    pf.start = 0;
    pf.end = 7;
    pf.parents[7] = 3;
    pf.parents[3] = 0;
    // Ensure the intermediate cell is not already marked as PATH.
    pf.state[3] &= ~PATH_FINDER_MASK_PATH;
    // Reconstruct the path.
    path_finder_reconstruct_path(&pf);
    // The intermediate cell (index 3) should now have the PATH flag.
    assert(pf.state[3] & PATH_FINDER_MASK_PATH);
    // The start cell should remain unmarked.
    assert(!(pf.state[0] & PATH_FINDER_MASK_PATH));
    printf("test_reconstruct_path passed.\n");
}

// ----------------------------------------------------------------------
// Test the fill function using both an always-passable and a never-passable function.
void test_fill() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    pf.fill_func = always_passable;
    memset(pf.state, 0, sizeof(pf.state));
    path_finder_fill(&pf);
    // All cells should be marked as passable.
    for (int32_t i = 0; i < pf.rows * pf.cols; i++) {
        assert((pf.state[i] & PATH_FINDER_MASK_PASSABLE) == PATH_FINDER_MASK_PASSABLE);
    }
    // Now use never_passable. Pre-set the state to all ones.
    pf.fill_func = never_passable;
    memset(pf.state, 0xFF, sizeof(pf.state));
    path_finder_fill(&pf);
    for (int32_t i = 0; i < pf.rows * pf.cols; i++) {
        assert((pf.state[i] & PATH_FINDER_MASK_PASSABLE) == 0);
    }
    printf("test_fill (both always and never) passed.\n");
}

// ----------------------------------------------------------------------
// Test that starting the search marks the start cell as open.
void test_begin() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    memset(pf.state, 0, sizeof(pf.state));
    path_finder_set_start(&pf, 1, 2);  // Sets start to index = 1 + 2*cols.
    path_finder_begin(&pf);
    assert((pf.state[pf.start] & PATH_FINDER_MASK_OPEN) == PATH_FINDER_MASK_OPEN);
    printf("test_begin passed.\n");
}

// ----------------------------------------------------------------------
// Test a single step (and full search) in a simple scenario.
// Create a 3x3 grid with start at (0,0) and end at (0,1) so that the neighbor is immediately adjacent.

void test_find_step_single_neighbor() {
    struct path_finder pf;
    pf.rows = 3;
    pf.cols = 3;
    memset(pf.state, 0, sizeof(pf.state));
    // Initialize scores high.
    for (int i = 0; i < pf.rows * pf.cols; i++) {
        pf.g_score[i] = 1000;
        pf.f_score[i] = 1000;
    }
    pf.fill_func = always_passable;
    pf.score_func = zero_score;
    
    // IMPORTANT: fill the grid so every cell is marked passable.
    path_finder_fill(&pf);
    
    path_finder_set_start(&pf, 0, 0);  // index 0.
    path_finder_set_end(&pf, 0, 1);    // index 3 (with 3 columns).
    path_finder_clear_path(&pf);
    // Mark the start cell as open.
    pf.state[pf.start] |= PATH_FINDER_MASK_OPEN;
    pf.g_score[pf.start] = 0;
    pf.f_score[pf.start] = path_finder_heuristic(&pf, pf.start);
    // Run one step.
    uint8_t run = path_finder_find_step(&pf, NULL);
    // Expect that the neighbor (the end cell at index 3) becomes open.
    assert((pf.state[3] & PATH_FINDER_MASK_OPEN) == PATH_FINDER_MASK_OPEN);
    // Since the end wasn’t reached yet, run should be 1.
    assert(run == 1);
    // Continue stepping until done.
    while (path_finder_find_step(&pf, NULL))
        ;
    // After completion, the algorithm should indicate a path was found.
    assert(pf.has_path == 1);
    // The end cell should now be marked as part of the path.
    assert((pf.state[pf.end] & PATH_FINDER_MASK_PATH) == PATH_FINDER_MASK_PATH);
    printf("test_find_step and overall find process passed.\n");
}

// ----------------------------------------------------------------------
// Test getter functions for cell properties.
void test_getters() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    memset(pf.state, 0, sizeof(pf.state));
    // Manually set flags for specific cells.
    pf.state[7] = PATH_FINDER_MASK_PASSABLE | PATH_FINDER_MASK_OPEN;
    pf.state[8] = PATH_FINDER_MASK_CLOSED;
    pf.state[9] = PATH_FINDER_MASK_PATH;
    path_finder_set_start(&pf, 2, 1);  // Index = 2 + 1*cols.
    path_finder_set_end(&pf, 3, 3);    // Index = 3 + 3*cols.
    // Compare getter returns with the underlying state.
    assert(path_finder_is_passable(&pf, 2, 2) == ((pf.state[2 + 2 * pf.cols] & PATH_FINDER_MASK_PASSABLE) == PATH_FINDER_MASK_PASSABLE));
    assert(path_finder_is_open(&pf, 2, 1) == ((pf.state[2 + 1 * pf.cols] & PATH_FINDER_MASK_OPEN) == PATH_FINDER_MASK_OPEN));
    assert(path_finder_is_closed(&pf, 2, 2) == ((pf.state[2 + 2 * pf.cols] & PATH_FINDER_MASK_CLOSED) == PATH_FINDER_MASK_CLOSED));
    assert(path_finder_is_path(&pf, 2, 2) == ((pf.state[2 + 2 * pf.cols] & PATH_FINDER_MASK_PATH) == PATH_FINDER_MASK_PATH));
    assert(path_finder_is_start(&pf, 2, 1) == 1);
    assert(path_finder_is_end(&pf, 3, 3) == 1);
    printf("test_getters passed.\n");
}

// ----------------------------------------------------------------------
// Test the initialize function.
void test_initialize() {
    struct path_finder pf;
    // Pre-set fields to nonzero values.
    memset(&pf, 0xFF, sizeof(pf));
    path_finder_initialize(&pf);
    for (int i = 0; i < PATH_FINDER_MAX_CELLS; i++) {
        assert(pf.parents[i] == 0);
        assert(pf.g_score[i] == 0);
        assert(pf.f_score[i] == 0);
        // After initialize, every cell should be marked passable.
        assert((pf.state[i] & PATH_FINDER_MASK_PASSABLE) == PATH_FINDER_MASK_PASSABLE);
    }
    // Also, rows, cols, start, end, and has_path should be zero.
    assert(pf.rows == 0);
    assert(pf.cols == 0);
    assert(pf.start == 0);
    assert(pf.end == 0);
    assert(pf.has_path == 0);
    printf("test_initialize passed.\n");
}

// ----------------------------------------------------------------------
// Test the full path finding process in a grid with all cells passable.
void test_find_path_success() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    pf.fill_func = always_passable;
    pf.score_func = zero_score;
    memset(pf.state, 0, sizeof(pf.state));
    memset(pf.parents, 0, sizeof(pf.parents));
    memset(pf.g_score, 0, sizeof(pf.g_score));
    memset(pf.f_score, 0, sizeof(pf.f_score));
    pf.has_path = 0;
    
    path_finder_fill(&pf);
    path_finder_set_start(&pf, 0, 0);
    path_finder_set_end(&pf, 4, 4);
    path_finder_clear_path(&pf);
    path_finder_find(&pf, NULL);
    assert(pf.has_path == 1);
    
    // Verify that following the parent chain from end eventually reaches start.
    int32_t current = pf.end;
    while (current != pf.start) {
        int32_t parent = pf.parents[current];
        assert(parent >= 0 && parent < pf.rows * pf.cols);
        current = parent;
    }
    printf("test_find_path_success passed.\n");
}

// ----------------------------------------------------------------------
// Test that the algorithm fails to find a path when no cell is passable.
void test_find_path_failure() {
    struct path_finder pf;
    pf.rows = GRID_ROWS;
    pf.cols = GRID_COLS;
    pf.fill_func = never_passable;
    memset(pf.state, 0, sizeof(pf.state));
    path_finder_fill(&pf);
    path_finder_set_start(&pf, 0, 0);
    path_finder_set_end(&pf, 4, 4);
    path_finder_clear_path(&pf);
    path_finder_find(&pf, NULL);
    assert(pf.has_path == 0);
    printf("test_find_path_failure passed.\n");
}

// ----------------------------------------------------------------------
// Main: Run all tests.
int main(void) {
    test_heuristic();
    test_open_set_empty();
    test_lowest_in_open_set();
    test_reconstruct_path();
    test_fill();
    test_begin();
    test_find_step_single_neighbor();
    test_getters();
    test_initialize();
    test_find_path_success();
    test_find_path_failure();
    printf("All detailed uastar tests passed.\n");
    return 0;
}