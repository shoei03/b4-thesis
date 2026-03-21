package jp.ac.osaka_u.sdl.nil.presenter.output

import jp.ac.osaka_u.sdl.nil.entity.CodeBlockInfo

/**
 * NIL's standard output format is "/path/to/file1,start_line1,end_line1,/path/to/file2,start_line2,end_line2,ngram_sim,lcs_sim",
 * as well as CCAligner.
 * Now includes method information if available and similarity metrics.
 */
class CSV : Format() {
    override fun reformat(
        codeBlock1: CodeBlockInfo, 
        codeBlock2: CodeBlockInfo,
        nGramSimilarity: String?,
        lcsSimilarity: String?
    ): String {
        val similarities = buildString {
            if (nGramSimilarity != null) {
                append(",").append(nGramSimilarity)
            }
            if (lcsSimilarity != null) {
                append(",").append(lcsSimilarity)
            }
        }
        return "${codeBlock1.toFullString()},${codeBlock2.toFullString()}$similarities"
    }
}
