package jp.ac.osaka_u.sdl.nil.usecase.preprocess

import io.reactivex.rxjava3.core.BackpressureStrategy
import io.reactivex.rxjava3.core.Flowable
import io.reactivex.rxjava3.core.Observable
import jp.ac.osaka_u.sdl.nil.NILConfig
import jp.ac.osaka_u.sdl.nil.entity.CodeBlock
import jp.ac.osaka_u.sdl.nil.entity.Parameter
import jp.ac.osaka_u.sdl.nil.util.toCharStream
import org.antlr.v4.runtime.CharStream
import org.antlr.v4.runtime.CommonTokenStream
import org.antlr.v4.runtime.Lexer
import org.antlr.v4.runtime.Parser
import org.antlr.v4.runtime.ParserRuleContext
import org.antlr.v4.runtime.Token
import org.antlr.v4.runtime.tree.ParseTreeListener
import org.antlr.v4.runtime.tree.ParseTreeWalker
import java.io.File

data class MethodInfo(
    val methodName: String?,
    val returnType: String?,
    val parameters: List<Parameter>?
)

abstract class AntlrTransformer(
    private val config: NILConfig,
    private val antlrLexer: (CharStream) -> Lexer,
    private val antlrParser: (CommonTokenStream) -> Parser,
) {
    fun extractBlocks(srcFile: File): Flowable<CodeBlock> =
        Observable.create<CodeBlock> { emitter ->
            val fileTokens: CommonTokenStream = srcFile.readText().toCharStream()
                .let(antlrLexer)
                .let(::CommonTokenStream)
                .apply { fill() }

            ParseTreeWalker.DEFAULT.walk(createVisitor { ctx: ParserRuleContext ->
                val startLine = ctx.start.line
                val endLine = ctx.stop.line
                if (endLine - startLine + 1 < config.minLine) {
                    return@createVisitor
                }
                val startToken: Int = ctx.sourceInterval.a
                val endToken: Int = ctx.sourceInterval.b
                val functionTokens = fileTokens.get(startToken, endToken).filterNot { it.isNegligible() }
                if (functionTokens.size >= config.minToken) {
                    val tokenSequence = SymbolSeparator.separate(functionTokens.map { it.text })
                    val methodInfo = extractMethodInfo(ctx)
                    emitter.onNext(
                        CodeBlock(
                            srcFile.canonicalPath,
                            startLine,
                            endLine,
                            tokenSequence,
                            methodInfo.methodName,
                            methodInfo.returnType,
                            methodInfo.parameters
                        )
                    )
                }
            }, antlrParser(fileTokens).extractRuleContext())
            emitter.onComplete()
        }.toFlowable(BackpressureStrategy.BUFFER)

    protected abstract fun createVisitor(action: (ParserRuleContext) -> Unit): ParseTreeListener
    protected abstract fun Parser.extractRuleContext(): ParserRuleContext
    protected abstract fun Token.isNegligible(): Boolean
    
    /**
     * Extract method information from the parse tree context.
     * Override this method to extract method name, return type, and parameters.
     * Default implementation returns null for all fields.
     */
    protected open fun extractMethodInfo(ctx: ParserRuleContext): MethodInfo =
        MethodInfo(null, null, null)
}
