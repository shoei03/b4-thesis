package jp.ac.osaka_u.sdl.nil.entity

import java.security.MessageDigest

/**
 * Parameter represents a function parameter with its name and type.
 */
data class Parameter(
    val name: String,
    val type: String
)

/**
 * Code block is a single function.
 */
data class CodeBlock(
    val fileName: String,
    val startLine: Int,
    val endLine: Int,
    val tokenSequence: TokenSequence,
    val methodName: String? = null,
    val returnType: String? = null,
    val parameters: List<Parameter>? = null,
    val commitHash: String? = null,
) {
    /**
     * Calculate MD5 hash of the token sequence for tracking method evolution
     */
    fun getTokenSequenceHash(): String {
        val content = tokenSequence.joinToString(",")
        return MessageDigest.getInstance("MD5")
            .digest(content.toByteArray())
            .joinToString("") { "%02x".format(it) }
    }

    override fun toString(): String {
        val tokenHash = getTokenSequenceHash()
        return if (methodName != null) {
            val paramStr = parameters?.joinToString(";") { 
                "${it.name.replace(",", ";")}:${it.type.replace(",", ";")}" 
            } ?: ""
            val returnTypeStr = returnType?.replace(",", ";") ?: "None"
            val commit = commitHash ?: "unknown"
            val tokenSeq = "[${tokenSequence.joinToString(";")}]"
            "${tokenHash},${fileName},${startLine},${endLine},${methodName},${returnTypeStr},[${paramStr}],${commit},${tokenSeq}"
        } else {
            "${tokenHash},${fileName},${startLine},${endLine}"
        }
    }
}
