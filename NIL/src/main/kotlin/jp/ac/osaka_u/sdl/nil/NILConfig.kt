package jp.ac.osaka_u.sdl.nil

import java.io.File

data class NILConfig(
    val src: File,
    val minLine: Int = 6,
    val minToken: Int = 50,
    val gramSize: Int = 5,
    val partitionNum: Int = 10,
    val filtrationThreshold: Int = 10,
    val verificationThreshold: Int = 70,
    val outputFileName: String = "result.csv",
    val threads: Int = 0,
    val lang: Language = Language.JAVA,
    val isForBigCloneEval: Boolean = false,
    val isForMutationInjectionFramework: Boolean = false,
    val isFullPathOutput: Boolean = false,
    val commitHash: String? = null,
    val commitTimestamp: String? = null,
)

fun parseArgs(args: Array<String>): NILConfig {
    var src: File? = null
    var minLine = 6
    var minToken = 50
    var gramSize = 5
    var partitionNum = 10
    var filtrationThreshold = 10
    var verificationThreshold = 70
    var outputFileName: String? = null
    var threads = 0
    var lang = Language.JAVA
    var isForBigCloneEval = false
    var isForMutationInjectionFramework = false
    var isFullPathOutput = false
    var commitHash: String? = null
    var commitTimestamp: String? = null

    val iterator = args.iterator()
    while (iterator.hasNext()) {
        when (val optionName = iterator.next().lowercase()) {
            "-s", "--src" -> src = File(iterator.next())
            "-mil", "--min-line" -> minLine = iterator.next().toIntOrException(optionName)
            "-mit", "--min-token" -> minToken = iterator.next().toIntOrException(optionName)
            "-n", "--n-gram" -> gramSize = iterator.next().toIntOrException(optionName)
            "-p", "--partition-number" -> partitionNum = iterator.next().toIntOrException(optionName)
            "-f", "--filtration-threshold" -> filtrationThreshold = iterator.next().toIntOrException(optionName)
            "-v", "--verification-threshold" -> verificationThreshold = iterator.next().toIntOrException(optionName)
            "-o", "--output" -> outputFileName = iterator.next()
            "-t", "--threads" -> threads = iterator.next().toInt()
            "-l", "--language" -> lang = iterator.next().toLangOrException()
            "-bce", "--bigcloneeval" -> isForBigCloneEval = true
            "-mif", "--mutationinjectionframework" -> isForMutationInjectionFramework = true
            "--full-path" -> isFullPathOutput = true
            "-ch", "--commit-hash" -> commitHash = iterator.next()
            "-ct", "--commit-timestamp" -> commitTimestamp = iterator.next()
            else -> throw InvalidOptionException("$optionName is invalid option.")
        }
    }

    if (isForBigCloneEval && isForMutationInjectionFramework) {
        throw InvalidOptionException("Cannot specify both -bce and -mif.")
    }
    
    // --full-path implies full path output, but -bce also requires full path
    val fullPathOutput = isFullPathOutput || isForBigCloneEval

    return NILConfig(
        src ?: throw InvalidOptionException("-s must be specified."),
        minLine,
        minToken,
        gramSize,
        partitionNum,
        filtrationThreshold,
        verificationThreshold,
        outputFileName ?: "result_${gramSize}_${filtrationThreshold}_${verificationThreshold}.csv",
        threads,
        lang,
        isForBigCloneEval,
        isForMutationInjectionFramework,
        fullPathOutput,
        commitHash,
        commitTimestamp,
    )
}

fun String.toIntOrException(optionName: String): Int =
    try {
        this.toInt()
    } catch (e: NumberFormatException) {
        throw InvalidOptionException("$optionName value $this is not integer.")
    }

fun String.toLangOrException(): Language =
    when (this.lowercase()) {
        "java" -> Language.JAVA
        "c" -> Language.C
        "cpp" -> Language.CPP
        "cs", "csharp" -> Language.CS
        "py", "python" -> Language.PYTHON
        "kt", "kotlin" -> Language.KOTLIN
        else -> throw InvalidOptionException("Language $this is invalid.")
    }

class InvalidOptionException(private val option: String) : RuntimeException() {
    override val message: String
        get() = """$option
            |-s, --src${'\t'}${'\t'}${'\t'}${'\t'}Source directory (must be specified)
            |-mil, --min-line${'\t'}${'\t'}${'\t'}Minimum line (default: 6)
            |-mit, --min-token${'\t'}${'\t'}${'\t'}Minimum token (default: 50)
            |-n, --n-gram${'\t'}${'\t'}${'\t'}${'\t'}N of N-gram (default: 5)
            |-p, --partition-number${'\t'}${'\t'}${'\t'}The number of partition (default: 10)   
            |-f, --filtration-threshold${'\t'}${'\t'}Filtration threshold (default: 10%)
            |-v, --verification-threshold${'\t'}${'\t'}Verification threshold (default: 70%)
            |-o, --output${'\t'}${'\t'}${'\t'}${'\t'}Output file path (can include directory) (default: result_{N-gram}_{filtering_threshold}_{verifying_threshold}.csv)
            |-t, --threads${'\t'}${'\t'}${'\t'}${'\t'}The number of threads used for parallel execution (default: all threads)
            |-l, --language${'\t'}${'\t'}${'\t'}${'\t'}Target language (default: java)
            |-bce, --bigcloneeval${'\t'}${'\t'}${'\t'}Output result feasible to BigCloneEval (default: false)
            |-mif, --mutationinjectionframework${'\t'}Output result feasible to MutationInjectionFramework (default: false)
            |--full-path${'\t'}${'\t'}${'\t'}${'\t'}Output result with full file paths instead of IDs (default: false)
            |-ch, --commit-hash${'\t'}${'\t'}${'\t'}Commit hash for tracking (optional)
            |-ct, --commit-timestamp${'\t'}${'\t'}Commit timestamp for tracking (optional)
        """.trimMargin()
}

enum class Language {
    JAVA, CPP, C, CS, PYTHON, KOTLIN
}
