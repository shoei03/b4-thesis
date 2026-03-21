package jp.ac.osaka_u.sdl.nil

import io.reactivex.rxjava3.core.Flowable
import io.reactivex.rxjava3.schedulers.Schedulers
import jp.ac.osaka_u.sdl.nil.entity.HuntSzymanskiLCS
import jp.ac.osaka_u.sdl.nil.entity.InvertedIndex
import jp.ac.osaka_u.sdl.nil.entity.TokenSequence
import jp.ac.osaka_u.sdl.nil.presenter.logger.LoggerWrapperFactory
import jp.ac.osaka_u.sdl.nil.presenter.output.FormatFactory
import jp.ac.osaka_u.sdl.nil.usecase.cloneDetection.LCSBasedVerification
import jp.ac.osaka_u.sdl.nil.usecase.cloneDetection.NGramBasedFiltration
import jp.ac.osaka_u.sdl.nil.usecase.cloneDetection.NGramBasedLocation
import jp.ac.osaka_u.sdl.nil.usecase.cloneDetection.OptimizedCloneDetection
import jp.ac.osaka_u.sdl.nil.usecase.preprocess.PreprocessFactory
import jp.ac.osaka_u.sdl.nil.util.parallelIfSpecified
import jp.ac.osaka_u.sdl.nil.util.toTime
import java.io.File
import java.nio.file.Files
import java.nio.file.Paths
import java.security.MessageDigest
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class NILMain(private val config: NILConfig) {
    companion object {
        const val RESULTS_DIR = "results"
        const val CODE_BLOCK_FILE_NAME = "code_blocks.csv"
        const val CLONE_PAIR_FILE_NAME = "clone_pairs.csv"
        const val RESULT_FILE_NAME = "result.csv"
        
        /**
         * Generate a short hash from a string
         */
        fun generateShortHash(input: String): String {
            val md = MessageDigest.getInstance("SHA-256")
            val digest = md.digest(input.toByteArray())
            return digest.joinToString("") { "%02x".format(it) }.take(8)
        }
        
        /**
         * Generate output directory path with timestamp and hash
         */
        fun generateOutputDir(sourceDir: File, commitTimestamp: String?, commitHash: String?): String {
            val timestamp = commitTimestamp ?: LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
            val hash = commitHash?.take(8) ?: generateShortHash(sourceDir.absolutePath)
            return "${RESULTS_DIR}/${timestamp}_${hash}"
        }
    }

    private val logger =
        LoggerWrapperFactory.create(config.isForMutationInjectionFramework, this.javaClass, config.outputFileName)

    fun run() {
        val startTime = System.currentTimeMillis()
        logger.infoStart()

        // Generate output directory
        val outputDir = generateOutputDir(config.src, config.commitTimestamp, config.commitHash)
        Files.createDirectories(Paths.get(outputDir))
        
        // Define file paths
        val codeBlockFilePath = Paths.get(outputDir, CODE_BLOCK_FILE_NAME).toString()
        val clonePairFilePath = Paths.get(outputDir, CLONE_PAIR_FILE_NAME).toString()
        val resultFilePath = Paths.get(outputDir, RESULT_FILE_NAME).toString()

        val (tokenSequences, tokenHashes) = PreprocessFactory.create(config).collectTokenSequences(config.src, codeBlockFilePath)
        logger.infoPreprocessCompletion(tokenSequences.size)
        
        // Code blocks are already saved by Preprocess.collectTokenSequences()

        val partitionSize = (tokenSequences.size + config.partitionNum - 1) / config.partitionNum
        val filtrationPhase = NGramBasedFiltration(config.filtrationThreshold)
        val filtrationBasedVerificationPhase = NGramBasedFiltration(config.verificationThreshold)
        val verificationPhase = LCSBasedVerification(HuntSzymanskiLCS(), config.verificationThreshold)

        File(clonePairFilePath).bufferedWriter().use { bw ->
            repeat(config.partitionNum) { i ->
                val startIndex: Int = i * partitionSize
                
                // Skip if startIndex exceeds the number of token sequences
                if (startIndex >= tokenSequences.size) {
                    return@repeat
                }

                val invertedIndex =
                    InvertedIndex.create(partitionSize, config.gramSize, tokenSequences, startIndex)
                logger.infoInvertedIndexCreationCompletion(i + 1)

                val locationPhase = NGramBasedLocation(invertedIndex)
                val cloneDetection =
                    OptimizedCloneDetection(
                        locationPhase,
                        filtrationPhase,
                        filtrationBasedVerificationPhase,
                        verificationPhase,
                        tokenSequences,
                        config.gramSize
                    )
                
                // Calculate the count for Flowable.range
                val count = tokenSequences.size - startIndex - 1
                if (count <= 0) {
                    logger.infoCloneDetectionCompletion(i + 1)
                    return@repeat
                }
                
                Flowable.range(startIndex + 1, count)
                    .parallelIfSpecified(config.threads)
                    .runOn(Schedulers.computation())
                    .flatMap { cloneDetection.exec(it) }
                    .sequential()
                    .blockingSubscribe { result ->
                        val lcsStr = result.lcsSimilarity?.toString() ?: ""
                        val hash1 = tokenHashes[result.id1]
                        val hash2 = tokenHashes[result.id2]
                        bw.appendLine("${hash1},${hash2},${result.nGramSimilarity},$lcsStr")
                    }
                logger.infoCloneDetectionCompletion(i + 1)
            }
        }
        val endTime = System.currentTimeMillis()
        logger.infoEnd((endTime - startTime).toTime())

        FormatFactory.create(config.isForBigCloneEval, config.isFullPathOutput)
            .convert(resultFilePath, codeBlockFilePath, clonePairFilePath)
    }
}

fun main(args: Array<String>) {
    val config: NILConfig = parseArgs(args)
    NILMain(config).run()
}
