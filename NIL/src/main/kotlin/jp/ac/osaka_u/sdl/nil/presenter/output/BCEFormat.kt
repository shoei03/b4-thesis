package jp.ac.osaka_u.sdl.nil.presenter.output

import jp.ac.osaka_u.sdl.nil.entity.CodeBlockInfo
import java.io.File

/**
 * BigCloneEval Format is as "dir1,file_name1,start_line1,end_line1,dir2,file_name2,start_line2,end_line2,ngram_sim,lcs_sim"
 */
class BCEFormat : Format() {
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
        return "${extractBCEFormat(codeBlock1)},${extractBCEFormat(codeBlock2)}$similarities"
    }

    private fun extractBCEFormat(codeBlock: CodeBlockInfo): String {
        val (dirName, fileName) = codeBlock.fileName.split(File.separator)
            .let { it[it.size - 2] to it.last() }
        return "$dirName,$fileName,${codeBlock.startLine},${codeBlock.endLine}"
    }
}
