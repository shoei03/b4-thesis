package jp.ac.osaka_u.sdl.nil.entity

/**
 * CodeBlockInfo represents parsed information from code_blocks file.
 * This class is used for output formatting.
 */
data class CodeBlockInfo(
    val fileName: String,
    val startLine: Int,
    val endLine: Int,
    val methodName: String? = null,
    val returnType: String? = null,
    val parameters: List<Parameter>? = null,
    val commitHash: String? = null,
    val tokenHash: String? = null,
    val tokenSequence: List<Int>? = null
) {
    companion object {
        /**
         * Parse a line from code_blocks file.
         * Supports multiple formats:
         * 
         * Token hash format: token_hash,/path/to/file,10,25
         * Token hash with method format: token_hash,/path/to/file,10,25,method_name,return_type,[param1:type1;param2:type2]
         * Token hash with extended format: token_hash,/path/to/file,10,25,method_name,return_type,[params],commit_hash,[tokens]
         */
        fun parse(line: String): CodeBlockInfo {
            val parts = line.split(",")
            
            // Check if first part is a token hash (32 hex characters)
            val hasTokenHash = parts.firstOrNull()?.matches(Regex("[0-9a-f]{32}")) == true
            
            // Skip token hash if present
            val effectiveParts = if (hasTokenHash) parts.drop(1) else parts
            
            return when {
                // Basic format: fileName,startLine,endLine
                effectiveParts.size == 3 -> {
                    CodeBlockInfo(
                        fileName = effectiveParts[0],
                        startLine = effectiveParts[1].toInt(),
                        endLine = effectiveParts[2].toInt()
                    )
                }
                // Extended format with commit hash and token sequence
                effectiveParts.size >= 7 -> {
                    val fileName = effectiveParts[0]
                    val startLine = effectiveParts[1].toInt()
                    val endLine = effectiveParts[2].toInt()
                    val methodName = effectiveParts[3]
                    val returnType = effectiveParts[4]
                    
                    // Parse parameters from [param1:type1;param2:type2;...]
                    // Find the parameters section between brackets
                    val paramStart = line.indexOf('[')
                    val paramEnd = line.indexOf(']', paramStart)
                    val paramString = if (paramStart >= 0 && paramEnd > paramStart) {
                        line.substring(paramStart + 1, paramEnd)
                    } else {
                        ""
                    }
                    val parameters = parseParameters(paramString)
                    
                    // Parse token sequence from [token1;token2;...]
                    // Find the token sequence section (last bracketed section)
                    val tokenSeqStart = line.lastIndexOf('[')
                    val tokenSeqEnd = line.lastIndexOf(']')
                    val tokenSequence = if (tokenSeqStart > paramEnd && tokenSeqEnd > tokenSeqStart) {
                        val tokenSeqString = line.substring(tokenSeqStart + 1, tokenSeqEnd)
                        if (tokenSeqString.isNotEmpty()) {
                            tokenSeqString.split(";").mapNotNull { it.toIntOrNull() }
                        } else {
                            null
                        }
                    } else {
                        null
                    }
                    
                    // Get commit hash
                    // It is between the parameter bracket and token sequence bracket
                    val afterParams = if (paramEnd >= 0) line.substring(paramEnd + 1) else line
                    val beforeTokenSeq = if (tokenSeqStart > paramEnd) {
                        afterParams.substring(0, tokenSeqStart - paramEnd - 1)
                    } else {
                        afterParams
                    }
                    val hashParts = beforeTokenSeq.split(",").filter { it.isNotEmpty() }
                    val commitHash = hashParts.lastOrNull()
                    
                    CodeBlockInfo(
                        fileName = fileName,
                        startLine = startLine,
                        endLine = endLine,
                        methodName = methodName.takeIf { it.isNotEmpty() && it != "null" },
                        returnType = returnType.takeIf { it.isNotEmpty() && it != "null" && it != "None" },
                        parameters = parameters,
                        commitHash = commitHash?.takeIf { it.isNotEmpty() && it != "null" && it != "unknown" },
                        tokenHash = null, // Token hash is in the first column, not stored in CodeBlockInfo
                        tokenSequence = tokenSequence
                    )
                }
                // Method format: fileName,startLine,endLine,methodName,returnType,[params]
                effectiveParts.size >= 6 -> {
                    val fileName = effectiveParts[0]
                    val startLine = effectiveParts[1].toInt()
                    val endLine = effectiveParts[2].toInt()
                    val methodName = effectiveParts[3]
                    val returnType = effectiveParts[4]
                    
                    // Parse parameters from [param1:type1;param2:type2;...]
                    val paramString = effectiveParts.drop(5).joinToString(",") // Re-join in case params contain commas
                    val parameters = parseParameters(paramString)
                    
                    CodeBlockInfo(
                        fileName = fileName,
                        startLine = startLine,
                        endLine = endLine,
                        methodName = methodName.takeIf { it.isNotEmpty() && it != "null" },
                        returnType = returnType.takeIf { it.isNotEmpty() && it != "null" && it != "None" },
                        parameters = parameters
                    )
                }
                else -> {
                    throw IllegalArgumentException("Invalid code block format: $line")
                }
            }
        }
        
        private fun parseParameters(paramString: String): List<Parameter>? {
            if (paramString.isEmpty() || paramString == "[]") {
                return null
            }
            
            // Remove surrounding brackets
            val cleaned = paramString.trim().removeSurrounding("[", "]")
            if (cleaned.isEmpty()) {
                return null
            }
            
            // Split by semicolon to get individual parameters
            return cleaned.split(";").mapNotNull { param ->
                val parts = param.split(":")
                if (parts.size == 2) {
                    Parameter(parts[0].trim(), parts[1].trim())
                } else {
                    null
                }
            }.takeIf { it.isNotEmpty() }
        }
    }
    
    /**
     * Convert to basic string format (fileName,startLine,endLine)
     * for backward compatibility.
     */
    fun toBasicString(): String = "$fileName,$startLine,$endLine"
    
    /**
     * Convert to full string format including method information.
     */
    fun toFullString(): String {
        return if (methodName != null) {
            // Replace commas with semicolons in parameter names and types to avoid CSV parsing issues
            val paramStr = parameters?.joinToString(";") { 
                "${it.name.replace(",", ";")}:${it.type.replace(",", ";")}" 
            } ?: ""
            // Replace commas in return type as well
            val sanitizedReturnType = (returnType ?: "None").replace(",", ";")
            "$fileName,$startLine,$endLine,$methodName,$sanitizedReturnType,[$paramStr]"
        } else {
            toBasicString()
        }
    }
}
