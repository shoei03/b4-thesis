import bisect
from collections import defaultdict

class NILCloneDetector:
    """
    NIL: Large-Scale Detection of Large-Variance Clones
    Based on the paper by Tasuku Nakagawa et al. (ESEC/FSE 2021)
    """

    def __init__(self, n_gram_size: int = 5, filter_threshold: float = 0.1, verify_threshold: float = 0.7):
        """
        [cite_start]:param n_gram_size: Size of N-gram (N). Recommended: 5 [cite: 514]
        :param filter_threshold: Threshold for filtration phase (theta). [cite_start]Recommended: 0.1 [cite: 508]
        :param verify_threshold: Threshold for verification phase (delta). [cite_start]Recommended: 0.7 [cite: 507]
        """
        self.n = n_gram_size
        self.theta = filter_threshold
        self.delta = verify_threshold
        
        self.inverted_index = defaultdict(list)
        self.code_blocks = []

    def preprocess(self, code_blocks: list[list[int]]):
        """
        Constructs an inverted index from code blocks.
        Corresponds to Section 3.1 and Algorithm 1 (conceptually).
        """
        self.code_blocks = code_blocks
        self.inverted_index.clear()

        for idx, block in enumerate(code_blocks):
            for gram in self._generate_ngrams(block):
                self.inverted_index[gram].append(idx)

    def detect_clones(self) -> list[tuple[int, int]]:
        """
        Executes the clone detection process consisting of three phases:
        1. Location
        2. Filtration
        3. Verification
        
        [cite_start]Corresponds to Algorithm 1 [cite: 358-438].
        """
        clone_pairs = set()

        for idx, target_block in enumerate(self.code_blocks):
            if len(target_block) < self.n:
                continue
            
            # Phase 1: Location - Find potential candidates using inverted index
            candidates = self._locate_candidates(idx, target_block)

            # Phase 2: Filtration - Filter candidates by N-gram overlap
            filtered_candidates = self._filter_candidates(target_block, candidates)

            # Phase 3: Verification - Verify using LCS-based similarity
            for candidate_idx in filtered_candidates:
                if self._verify_candidate(target_block, self.code_blocks[candidate_idx]):
                    clone_pairs.add((idx, candidate_idx))

        return list(clone_pairs)

    # -------------------------------------------------------------------------
    # Internal Methods (Phases)
    # -------------------------------------------------------------------------

    def _locate_candidates(self, target_idx: int, target_block: list[int]) -> set[int]:
        """
        Location Phase: Collects clone candidates using the inverted index.
        [cite_start]Algorithm 1 Lines 3-12 [cite: 366-390].
        """
        candidates = set()
        target_ngrams = self._generate_ngrams(target_block)

        for gram in target_ngrams:
            if gram in self.inverted_index:
                candidates.update(self.inverted_index[gram])
        
        # Avoid self-comparison and duplicate pairs (i, j) vs (j, i)
        return {c for c in candidates if c > target_idx}

    def _filter_candidates(self, target_block: list[int], candidates: set[int]) -> list[int]:
        """
        Filtration Phase: Filters candidates based on N-gram overlap ratio.
        [cite_start]Algorithm 1 Lines 14-23 [cite: 391-402].
        """
        target_ngrams = self._generate_ngrams(target_block)
        target_ngram_count = len(target_ngrams)
        qualified_candidates = []

        for candidate_idx in candidates:
            candidate_block = self.code_blocks[candidate_idx]
            candidate_ngrams = self._generate_ngrams(candidate_block)
            
            # [cite_start]Calculate filtration_sim [cite: 461]
            common_ngrams = len(target_ngrams.intersection(candidate_ngrams))
            denominator = min(target_ngram_count, len(candidate_ngrams))

            if denominator > 0:
                filtration_sim = common_ngrams / denominator
                if filtration_sim >= self.theta:
                    qualified_candidates.append(candidate_idx)

        return qualified_candidates

    def _verify_candidate(self, target_block: list[int], candidate_block: list[int]) -> bool:
        """
        Verification Phase: Verifies clone pair using LCS-based similarity.
        [cite_start]Algorithm 1 Lines 25-33 [cite: 411-436].
        """
        lcs_len = self._compute_lcs_length_hunt_szymanski(target_block, candidate_block)
        
        # [cite_start]Calculate verification_sim [cite: 472-474]
        denominator = min(len(target_block), len(candidate_block))
        
        if denominator == 0:
            return False
            
        similarity = lcs_len / denominator
        return similarity >= self.delta

    # -------------------------------------------------------------------------
    # Internal Methods (Helpers)
    # -------------------------------------------------------------------------

    def _compute_lcs_length_hunt_szymanski(self, seq1: list[int], seq2: list[int]) -> int:
        """
        Computes LCS length using the Hunt-Szymanski algorithm.
        [cite_start]Reduces time complexity to O((r + n) log n) [cite: 483-484].
        """
        # Map token to indices in seq1
        indexes = defaultdict(list)
        for i, token in enumerate(seq1):
            indexes[token].append(i)
        
        # Sort indices in descending order for LIS processing
        for token in indexes:
            indexes[token].reverse()
        
        # Find match indices in seq1 for tokens in seq2
        match_indices = []
        for token in seq2:
            if token in indexes:
                match_indices.extend(indexes[token])
        
        # Compute LIS (Longest Increasing Subsequence) on match_indices
        tails = []
        for idx in match_indices:
            pos = bisect.bisect_left(tails, idx)
            if pos < len(tails):
                tails[pos] = idx
            else:
                tails.append(idx)
        
        return len(tails)

    def _generate_ngrams(self, token_seq: list[int]) -> set[tuple]:
        """Generates a set of N-grams from a token sequence."""
        if len(token_seq) < self.n:
            return set()
        return {tuple(token_seq[i : i + self.n]) for i in range(len(token_seq) - self.n + 1)}