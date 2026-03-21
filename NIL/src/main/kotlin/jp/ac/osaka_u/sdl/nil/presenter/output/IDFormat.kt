package jp.ac.osaka_u.sdl.nil.presenter.output

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption

/**
 * IDFormat simply copies clone_pairs.csv to the result file.
 * This format is the most compact, using only IDs instead of full file paths.
 * To interpret the results, users need to reference the code_blocks.csv file.
 * 
 * Output format: id1,id2,ngram_similarity,lcs_similarity
 */
class IDFormat : Format() {
    override fun convert(resultFilePath: String, codeBlockFilePath: String, clonePairFilePath: String) {
        // Simply copy clone_pairs.csv to result.csv
        val clonePairFile = File(clonePairFilePath)
        val resultFile = File(resultFilePath)
        
        Files.copy(
            clonePairFile.toPath(),
            resultFile.toPath(),
            StandardCopyOption.REPLACE_EXISTING
        )
    }
}
