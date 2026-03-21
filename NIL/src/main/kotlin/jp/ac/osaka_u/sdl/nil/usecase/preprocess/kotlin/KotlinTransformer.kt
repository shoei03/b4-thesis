package jp.ac.osaka_u.sdl.nil.usecase.preprocess.kotlin

import KotlinLexer
import KotlinParser
import KotlinParserBaseListener
import jp.ac.osaka_u.sdl.nil.NILConfig
import jp.ac.osaka_u.sdl.nil.entity.Parameter
import jp.ac.osaka_u.sdl.nil.usecase.preprocess.AntlrTransformer
import jp.ac.osaka_u.sdl.nil.usecase.preprocess.MethodInfo
import org.antlr.v4.runtime.Parser
import org.antlr.v4.runtime.ParserRuleContext
import org.antlr.v4.runtime.Token
import org.antlr.v4.runtime.tree.ParseTreeListener

class KotlinTransformer(config: NILConfig) :
    AntlrTransformer(
        config,
        ::KotlinLexer,
        ::KotlinParser
    ) {
    override fun createVisitor(action: (ParserRuleContext) -> Unit): ParseTreeListener =
        object : KotlinParserBaseListener() {
            override fun enterFunctionDeclaration(ctx: KotlinParser.FunctionDeclarationContext) =
                action(ctx)
        }

    override fun Parser.extractRuleContext(): ParserRuleContext =
        (this as KotlinParser).kotlinFile()

    override fun Token.isNegligible(): Boolean =
        this.text.run {
            this.isEmpty() || this[0] == '\n' || this[0] == ' ' || this[0] == '\r' ||
                this.startsWith("//") || this.startsWith("/*")
        }

    override fun extractMethodInfo(ctx: ParserRuleContext): MethodInfo {
        if (ctx !is KotlinParser.FunctionDeclarationContext) {
            return MethodInfo(null, null, null)
        }

        // Extract method name from identifier
        val methodName = ctx.identifier()?.text

        // Extract return type from type() if present
        // In Kotlin grammar, multiple type() can exist (receiver type, return type)
        // The return type is after COLON, which is typically the last type() element
        val types = ctx.type()
        val returnType = if (types != null && types.isNotEmpty()) {
            // If there's a COLON, the type after it is the return type
            if (ctx.COLON() != null) {
                types.lastOrNull()?.text
            } else {
                null
            }
        } else {
            null
        }

        // Extract parameters from functionValueParameters
        val parameters = ctx.functionValueParameters()?.let { params ->
            extractParameters(params)
        }

        return MethodInfo(methodName, returnType, parameters)
    }

    private fun extractParameters(params: KotlinParser.FunctionValueParametersContext): List<Parameter> {
        val paramList = mutableListOf<Parameter>()

        params.functionValueParameter()?.forEach { paramCtx ->
            val parameter = paramCtx.parameter()
            val name = parameter.simpleIdentifier()?.text ?: "unknown"
            val type = parameter.type()?.text ?: "Any"
            paramList.add(Parameter(name, type))
        }

        return paramList
    }
}
