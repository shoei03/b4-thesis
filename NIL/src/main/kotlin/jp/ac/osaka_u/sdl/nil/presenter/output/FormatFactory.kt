package jp.ac.osaka_u.sdl.nil.presenter.output

class FormatFactory {
    companion object {
        fun create(isForBigCloneEval: Boolean, isFullPathOutput: Boolean): Format =
            when {
                // If neither BCE nor full-path is specified, use ID format (default)
                !isForBigCloneEval && !isFullPathOutput -> IDFormat()
                // If BCE is specified, use BCE format
                isForBigCloneEval -> BCEFormat()
                // If full-path is specified, use standard CSV format
                else -> CSV()
            }
    }
}
