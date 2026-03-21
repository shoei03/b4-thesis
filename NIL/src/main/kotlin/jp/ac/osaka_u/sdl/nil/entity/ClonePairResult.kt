package jp.ac.osaka_u.sdl.nil.entity

/**
 * Represents a clone pair detection result with similarity metrics
 * @param id1 First code block ID
 * @param id2 Second code block ID
 * @param nGramSimilarity N-gram based similarity percentage (0-100)
 * @param lcsSimilarity LCS based similarity percentage (0-100), null if not calculated
 */
data class ClonePairResult(
    val id1: Int,
    val id2: Int,
    val nGramSimilarity: Int,
    val lcsSimilarity: Int?
)
