package jp.ac.osaka_u.sdl.nil.presenter.output

import jp.ac.osaka_u.sdl.nil.entity.CodeBlockInfo
import java.io.File

abstract class Format {
    /**
     * Convert clone pairs to the final result format
     * @param resultFilePath Path to the result file to be created
     * @param codeBlockFilePath Path to the code_blocks file for reference
     * @param clonePairFilePath Path to the clone_pairs file (ID format)
     */
    open fun convert(resultFilePath: String, codeBlockFilePath: String, clonePairFilePath: String) {
        File(resultFilePath).bufferedWriter().use { bw ->
            val codeBlocks: List<CodeBlockInfo> = File(codeBlockFilePath)
                .readLines()
                .map { CodeBlockInfo.parse(it) }
                
            File(clonePairFilePath).bufferedReader().use { br ->
                br.lines()
                    .map { line ->
                        val parts = line.split(",")
                        val id1 = parts[0].toInt()
                        val id2 = parts[1].toInt()
                        val nGramSimilarity = if (parts.size > 2 && parts[2].isNotEmpty()) parts[2] else null
                        val lcsSimilarity = if (parts.size > 3 && parts[3].isNotEmpty()) parts[3] else null
                        val codeBlock1 = codeBlocks[id1]
                        val codeBlock2 = codeBlocks[id2]
                        reformat(codeBlock1, codeBlock2, nGramSimilarity, lcsSimilarity)
                    }
                    .forEach { bw.appendLine(it) }
            }
        }
    }

    protected open fun reformat(
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
