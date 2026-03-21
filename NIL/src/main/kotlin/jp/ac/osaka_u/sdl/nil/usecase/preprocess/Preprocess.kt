package jp.ac.osaka_u.sdl.nil.usecase.preprocess

import io.reactivex.rxjava3.core.Flowable
import io.reactivex.rxjava3.schedulers.Schedulers
import jp.ac.osaka_u.sdl.nil.entity.CodeBlock
import jp.ac.osaka_u.sdl.nil.entity.TokenSequence
import jp.ac.osaka_u.sdl.nil.util.parallelIfSpecified
import java.io.File

/**
 * This is an abstract class for Preprocessing phase.
 * If you want to extend NIL to multiple languages,
 * all you have to do is extend this class
 * and write methods to collect the source files and code blocks of the language.
 */
abstract class Preprocess(private val threads: Int, private val commitHash: String? = null, private val commitTimestamp: String? = null) {

    fun collectTokenSequences(src: File, codeBlockFilePath: String): Pair<List<TokenSequence>, List<String>> {
        val codeBlockFile = File(codeBlockFilePath)
        
        // Create parent directory if it doesn't exist
        codeBlockFile.parentFile?.mkdirs()
        
        // List to store token hashes
        val tokenHashes = mutableListOf<String>()
        
        val tokenSequences = codeBlockFile.bufferedWriter().use { bw ->
            collectSourceFiles(src)
                .parallelIfSpecified(threads)
                .runOn(Schedulers.io())
                .flatMap { collectBlocks(it) }
                .sequential()
                .map { codeBlock -> 
                    // Add commit hash to code block if not already set
                    val blockWithCommit = if (commitHash != null && codeBlock.commitHash == null) {
                        codeBlock.copy(commitHash = commitHash)
                    } else {
                        codeBlock
                    }
                    // Calculate and store token hash
                    val tokenHash = blockWithCommit.getTokenSequenceHash()
                    tokenHashes.add(tokenHash)
                    
                    bw.appendLine(blockWithCommit.toString())
                    blockWithCommit
                }
                .map { it.tokenSequence }
                .toList()
                .blockingGet()
        }
        
        return Pair(tokenSequences, tokenHashes)
    }

    protected abstract fun collectSourceFiles(dir: File): Flowable<File>
    protected abstract fun collectBlocks(srcFile: File): Flowable<CodeBlock>
}
